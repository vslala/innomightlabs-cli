from common.decorators import Tool
from common.utils import console


@Tool
def shell_command(command: str) -> str:
    """
    Executes a shell command and returns the output.

    Args:
        command (str): The shell command to execute on the terminal as it is.
    Returns:
        str: The output from the executed command.
    """
    import subprocess

    console.print(f"Executing command: [dim yellow]{command}[/dim yellow]")
    result = subprocess.run(
        command,
        shell=True,
        check=False,
        capture_output=True,
        text=True,
    )

    stdout = result.stdout or ""
    stderr = result.stderr or ""

    if stdout and stderr:
        output = f"{stdout.rstrip()}\n{stderr.rstrip()}"
    else:
        output = stdout or stderr

    if output.strip():
        return output

    if result.returncode == 0:
        return "Command executed successfully with no output."

    return f"Command exited with status {result.returncode} and produced no output."
