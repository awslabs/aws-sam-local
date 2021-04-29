"""
Represents a manifest that lists the available SAM pipeline templates.
Example:
    providers:
      - displayName:Jenkins
        id: jenkins
      - displayName:Gitlab CI/CD
        id: gitlab
      - displayName:Github Actions
        id: github-actions
    templates:
      - displayName: jenkins-two-stages-pipeline
        provider: Jenkins
        location: templates/cookiecutter-jenkins-two-stages-pipeline
      - displayName: gitlab-two-stages-pipeline
        provider: Gitlab
        location: templates/cookiecutter-gitlab-two-stages-pipeline
      - displayName: Github-Actions-two-stages-pipeline
        provider: Github Actions
        location: templates/cookiecutter-github-actions-two-stages-pipeline
"""
from pathlib import Path
from typing import Dict, List

import yaml

from samcli.commands.exceptions import AppPipelineTemplateManifestException
from samcli.yamlhelper import parse_yaml_file


class Provider:
    """ CI/CD provider such as Jenkins, Gitlab and GitHub-Actions"""

    def __init__(self, manifest: Dict) -> None:
        self.id: str = manifest["id"]
        self.display_name: str = manifest["displayName"]


class PipelineTemplateMetadata:
    """ The metadata of a Given pipeline template"""

    def __init__(self, manifest: Dict) -> None:
        self.display_name: str = manifest["displayName"]
        self.provider: str = manifest["provider"]
        self.location: str = manifest["location"]


class PipelineTemplatesManifest:
    """ The metadata of the available CI/CD providers and the pipeline templates"""

    def __init__(self, manifest_path: Path) -> None:
        try:
            manifest: Dict = parse_yaml_file(file_path=str(manifest_path))
            self.providers: List[Provider] = list(map(Provider, manifest["providers"]))
            self.templates: List[PipelineTemplateMetadata] = list(map(PipelineTemplateMetadata, manifest["templates"]))
        except (FileNotFoundError, KeyError, TypeError, yaml.YAMLError) as ex:
            raise AppPipelineTemplateManifestException(
                "SAM pipeline templates manifest file is not found or ill-formatted. This could happen if the file "
                f"{manifest_path} got deleted or modified."
                "If you believe this is not the case, please file an issue at https://github.com/aws/aws-sam-cli/issues"
            ) from ex
