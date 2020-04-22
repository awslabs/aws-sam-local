"""
CLI command for "bootstrap", which sets up a SAM development environment
"""
import click

from samcli.cli.main import pass_context, common_options, aws_creds_options
from samcli.lib.telemetry.metrics import track_command
from samcli.lib.bootstrap import bootstrap

SHORT_HELP = "Set up development environment for AWS SAM applications."

HELP_TEXT = """
Sets up a development environment for AWS SAM applications.

Currently this creates, if one does not exist, a managed S3 bucket for your account in your working AWS region.
"""


@click.command("bootstrap", short_help=SHORT_HELP, help=HELP_TEXT, context_settings=dict(max_content_width=120))
@common_options
@aws_creds_options
@pass_context
@track_command
def cli(ctx):
    do_cli(ctx.region, ctx.profile, ctx.role_arn)  # pragma: no cover


def do_cli(region, profile, role_arn=None):
    bucket_name = bootstrap.manage_stack(profile=profile, region=region, role_arn=role_arn)
    click.echo("Source Bucket: " + bucket_name)
