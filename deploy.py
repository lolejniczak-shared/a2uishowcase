#!/usr/bin/env python3
"""Deploy or update `a2ui_showcase_agent` on Vertex AI Agent Runtime using `config.json`.

Separates:
- `location` (e.g. `us-central1`): Region where Agent Runtime & VertexAiSessionService run.
- `model_location` (e.g. `global`): Endpoint location where the Gemini LLM is called
  (injected into the runtime container via `env_vars={"GOOGLE_CLOUD_LOCATION": model_location}`).
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
from pathlib import Path
import sys

import cloudpickle
import google.adk
import pydantic
import vertexai
from vertexai.agent_engines import AdkApp

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "config.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="Deploy or update ADK A2UI Showcase Agent on Agent Runtime.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument(
        "--create",
        action="store_true",
        help="Force creating a new Reasoning Engine even if `reasoning_engine` is set in config.json",
    )
    args = parser.parse_args()

    if not args.config.exists():
        sys.exit(f"Error: Config file not found at {args.config}")

    with args.config.open("r", encoding="utf-8") as f:
        cfg = json.load(f)

    project_id = cfg.get("project_id", "").strip()
    if not project_id or project_id == "YOUR_PROJECT_ID":
        sys.exit(f"Error: Please set a valid 'project_id' in {args.config}")

    # 1. `location` is the regional Agent Runtime host (must be a region like us-central1)
    location = cfg.get("location", "us-central1").strip()
    # 2. `model_location` is the Gemini model endpoint region (can be "global" for global-only models)
    model_location = cfg.get("model_location", "global").strip()
    model_name = cfg.get("model_name", "gemini-2.5-flash").strip()

    staging_bucket = cfg.get("staging_bucket", f"gs://{project_id}-agent-staging").strip()
    if not staging_bucket.startswith("gs://"):
        staging_bucket = f"gs://{staging_bucket}"
    agent_package = cfg.get("agent_package", "a2ui_showcase_agent").strip()
    display_name = cfg.get("agent_display_name", "A2UI Component Showcase Agent").strip()
    description = cfg.get("agent_description", "").strip()
    existing_re = cfg.get("reasoning_engine", "").strip()

    # Keep Agent Engine / Session Service pinned to the regional `location` (e.g. us-central1),
    # while setting `GOOGLE_CLOUD_LOCATION` to `model_location` (e.g. global) for Gemini LLM calls.
    os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
    os.environ["GOOGLE_CLOUD_AGENT_ENGINE_LOCATION"] = location
    os.environ["GOOGLE_CLOUD_LOCATION"] = model_location
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "1"
    os.environ["MODEL_NAME"] = model_name

    agent_module = importlib.import_module(f"{agent_package}.agent")
    root_agent = agent_module.root_agent
    if model_name:
        root_agent.model = model_name

    # Initialize Vertex AI control plane in the regional Agent Runtime location (e.g. us-central1)
    vertexai.init(
        project=project_id,
        location=location,
        staging_bucket=staging_bucket,
    )

    app = AdkApp(
        agent=root_agent,
        enable_tracing=True,
    )

    requirements = [
        "google-cloud-aiplatform[agent_engines,adk]>=1.129.0",
        "google-genai>=1.0.0",
        f"google-adk=={google.adk.__version__}",
        f"cloudpickle=={cloudpickle.__version__}",
        f"pydantic=={pydantic.VERSION}",
    ]

    # Pass GOOGLE_CLOUD_LOCATION="global" to the runtime container so google.genai.Client
    # calls the global Gemini endpoint while VertexAiSessionService uses us-central1.
    env_vars = {
        "GOOGLE_CLOUD_LOCATION": model_location,
        "MODEL_NAME": model_name,
    }

    print(
        f"Deploying '{display_name}'\n"
        f"  Agent Runtime Region : {location}\n"
        f"  Model Endpoint Region: {model_location}\n"
        f"  Model Name           : {model_name}"
    )

    if existing_re and not args.create:
        print(f"Updating existing Reasoning Engine '{existing_re}' in-place...")
        remote_agent = vertexai.agent_engines.update(
            resource_name=existing_re,
            agent_engine=app,
            requirements=requirements,
            extra_packages=[agent_package],
            env_vars=env_vars,
            display_name=display_name,
            description=description or root_agent.description,
            gcs_dir_name=f"agent_engine/{agent_package}",
        )
    else:
        print(f"Creating new Reasoning Engine '{display_name}' in {project_id} ({location})...")
        remote_agent = vertexai.agent_engines.create(
            agent_engine=app,
            requirements=requirements,
            extra_packages=[agent_package],
            env_vars=env_vars,
            display_name=display_name,
            description=description or root_agent.description,
            gcs_dir_name=f"agent_engine/{agent_package}",
        )

    resource_name = remote_agent.resource_name
    print(f"\nDeployment succeeded!\n  Reasoning Engine: {resource_name}")

    cfg["reasoning_engine"] = resource_name
    with args.config.open("w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
        f.write("\n")
    print(f"Saved 'reasoning_engine' to {args.config}")


if __name__ == "__main__":
    main()