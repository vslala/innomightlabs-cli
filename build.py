#!/usr/bin/env python3
"""
Build script for InnomightLabs CLI
Cross-platform PyInstaller build automation with error handling
"""

import sys
import os
import subprocess
import shutil
import argparse
import tarfile
import hashlib
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Tuple

# ANSI color codes for cross-platform colored output
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

    @staticmethod
    def disable_colors():
        """Disable colors for non-terminal environments"""
        for attr in dir(Colors):
            if not attr.startswith('_') and attr != 'disable_colors':
                setattr(Colors, attr, '')

# Disable colors on Windows without ANSI support or non-terminals
if os.name == 'nt' and 'ANSICON' not in os.environ:
    try:
        import colorama
        colorama.init()
    except ImportError:
        Colors.disable_colors()
elif not sys.stdout.isatty():
    Colors.disable_colors()


class BuildManager:
    """Manages the PyInstaller build process"""
    
    def __init__(self, build_type: str = 'development'):
        self.build_type = build_type
        self.project_root = Path.cwd()
        self.spec_file = self.project_root / 'innomightlabs-cli.spec'
        self.dist_dir = self.project_root / 'dist'
        self.build_dir = self.project_root / 'build'
        
    def print_header(self, message: str) -> None:
        """Print a formatted header message"""
        print(f"\n{Colors.CYAN}{Colors.BOLD}{'='*60}{Colors.END}")
        print(f"{Colors.CYAN}{Colors.BOLD}{message.center(60)}{Colors.END}")
        print(f"{Colors.CYAN}{Colors.BOLD}{'='*60}{Colors.END}\n")
        
    def print_step(self, step: str) -> None:
        """Print a build step message"""
        print(f"{Colors.BLUE}► {step}{Colors.END}")
        
    def print_success(self, message: str) -> None:
        """Print a success message"""
        print(f"{Colors.GREEN}✓ {message}{Colors.END}")
        
    def print_warning(self, message: str) -> None:
        """Print a warning message"""
        print(f"{Colors.YELLOW}⚠ {message}{Colors.END}")
        
    def print_error(self, message: str) -> None:
        """Print an error message"""
        print(f"{Colors.RED}✗ {message}{Colors.END}")
        
    def run_command(self, cmd: List[str], description: str, 
                   capture_output: bool = False) -> Optional[str]:
        """Run a command with error handling"""
        try:
            self.print_step(f"{description}...")
            if capture_output:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                return result.stdout.strip()
            else:
                subprocess.run(cmd, check=True)
                self.print_success(f"{description} completed")
                return None
        except subprocess.CalledProcessError as e:
            self.print_error(f"{description} failed: {e}")
            if capture_output and e.stdout:
                print(f"STDOUT: {e.stdout}")
            if capture_output and e.stderr:
                print(f"STDERR: {e.stderr}")
            return None
        except FileNotFoundError:
            self.print_error(f"Command not found: {' '.join(cmd)}")
            return None
            
    def check_python_version(self) -> bool:
        """Check if Python version is compatible"""
        self.print_step("Checking Python version")
        version = sys.version_info
        if version.major == 3 and version.minor >= 8:
            self.print_success(f"Python {version.major}.{version.minor}.{version.micro} is compatible")
            return True
        else:
            self.print_error(f"Python {version.major}.{version.minor}.{version.micro} is not supported. Requires Python 3.8+")
            return False
            
    def check_spec_file(self) -> bool:
        """Check if the spec file exists"""
        self.print_step("Checking PyInstaller spec file")
        if self.spec_file.exists():
            self.print_success(f"Found spec file: {self.spec_file}")
            return True
        else:
            self.print_error(f"Spec file not found: {self.spec_file}")
            return False
            
    def install_pyinstaller(self) -> bool:
        """Install PyInstaller if not present"""
        try:
            # Check if PyInstaller is already installed
            result = self.run_command(
                [sys.executable, '-c', 'import PyInstaller; print(PyInstaller.__version__)'],
                "Checking PyInstaller installation",
                capture_output=True
            )
            
            if result:
                self.print_success(f"PyInstaller {result} is already installed")
                return True
        except:
            pass
            
        # Install PyInstaller
        self.print_step("Installing PyInstaller")
        cmd = [sys.executable, '-m', 'pip', 'install', 'pyinstaller']
        if self.run_command(cmd, "Installing PyInstaller") is not None:
            self.print_success("PyInstaller installed successfully")
            return True
        return False
        
    def cleanup_build_artifacts(self) -> None:
        """Clean up build artifacts"""
        self.print_step("Cleaning up build artifacts")
        
        dirs_to_clean = [self.build_dir, self.dist_dir]
        
        for dir_path in dirs_to_clean:
            if dir_path.exists():
                try:
                    shutil.rmtree(dir_path)
                    self.print_success(f"Removed {dir_path}")
                except OSError as e:
                    self.print_warning(f"Could not remove {dir_path}: {e}")
                    
    def build_executable(self) -> bool:
        """Run PyInstaller to build the executable"""
        self.print_step("Building executable with PyInstaller")
        
        # Prepare PyInstaller command
        cmd = [sys.executable, '-m', 'PyInstaller']
        
        # Add build type specific options
        if self.build_type == 'release':
            cmd.extend(['--clean', '--noconfirm'])
        else:  # development
            cmd.extend(['--clean', '--noconfirm', '--log-level=INFO'])
            
        # Add spec file
        cmd.append(str(self.spec_file))
        
        # Run the build
        env = os.environ.copy()
        pyinstaller_base = self.project_root / ".pyinstaller"
        config_dir = pyinstaller_base / "config"
        cache_dir = pyinstaller_base / "cache"
        temp_dir = pyinstaller_base / "temp"
        for directory in (config_dir, cache_dir, temp_dir):
            directory.mkdir(parents=True, exist_ok=True)

        env.setdefault("PYINSTALLER_CONFIG_DIR", str(config_dir))
        env.setdefault("PYINSTALLER_CACHE_DIR", str(cache_dir))
        env.setdefault("PYINSTALLER_TEMP_DIR", str(temp_dir))

        try:
            self.print_step(f"Running: {' '.join(cmd)}")
            subprocess.run(cmd, check=True, env=env)
            self.print_success("PyInstaller build completed successfully")
            return True
        except subprocess.CalledProcessError as e:
            self.print_error(f"PyInstaller build failed with exit code {e.returncode}")
            return False
            
    def find_executable(self) -> Optional[Path]:
        """Find the built executable"""
        self.print_step("Locating built executable")
        
        # Common executable names and locations
        exe_names = ['innomightlabs-cli', 'innomightlabs-cli.exe']
        search_dirs = [
            self.dist_dir / 'innomightlabs-cli',
            self.dist_dir,
        ]
        
        for search_dir in search_dirs:
            if search_dir.exists():
                for exe_name in exe_names:
                    exe_path = search_dir / exe_name
                    if exe_path.exists():
                        self.print_success(f"Found executable: {exe_path}")
                        return exe_path
                        
        self.print_error("Could not find built executable")
        return None

    def package_artifacts(
        self,
        executable: Path,
        artifact_name: Optional[str] = None,
        output_dir: Optional[Path] = None,
    ) -> Tuple[Path, Path]:
        """Create a compressed archive and checksum for the built executable."""
        if not executable.exists():
            raise FileNotFoundError(f"Executable not found at {executable}")

        if output_dir is None:
            output_dir = self.project_root / "release"
        output_dir.mkdir(parents=True, exist_ok=True)

        if artifact_name is None:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            artifact_name = f"innomightlabs-cli-macos-arm64-{timestamp}"

        archive_path = output_dir / f"{artifact_name}.tar.gz"
        checksum_path = output_dir / f"{artifact_name}.sha256"

        self.print_step(f"Creating artifact archive at {archive_path}")
        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(executable, arcname="innomightlabs-cli")

        self.print_step(f"Generating SHA256 checksum at {checksum_path}")
        sha256_hash = hashlib.sha256()
        with archive_path.open("rb") as artifact_file:
            for chunk in iter(lambda: artifact_file.read(8192), b""):
                sha256_hash.update(chunk)
        checksum_path.write_text(f"{sha256_hash.hexdigest()}  {archive_path.name}\n")

        self.print_success("Artifact packaging completed")
        return archive_path, checksum_path

    def create_artifact_only_release(
        self,
        artifacts: List[Path],
        branch_name: Optional[str] = None,
        tag_name: Optional[str] = None,
        commit_message: Optional[str] = None,
        push: bool = False,
    ) -> None:
        """Create an orphan branch that contains only the provided artifacts."""
        if not artifacts:
            raise ValueError("No artifacts provided for release branch creation.")

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        branch_name = branch_name or (f"artifacts/{tag_name}" if tag_name else f"artifacts/{timestamp}")
        commit_message = commit_message or f"Artifact release {tag_name or timestamp}"

        with tempfile.TemporaryDirectory(prefix="artifact_release_") as temp_dir:
            temp_path = Path(temp_dir)

            subprocess.run(
                ["git", "clone", "--no-checkout", str(self.project_root), str(temp_path)],
                cwd=self.project_root,
                check=True,
            )

            subprocess.run(
                ["git", "checkout", "--orphan", branch_name],
                cwd=temp_path,
                check=True,
            )

            for item in temp_path.iterdir():
                if item.name == ".git":
                    continue
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()

            release_dir = temp_path / "release"
            release_dir.mkdir(parents=True, exist_ok=True)

            for artifact in artifacts:
                shutil.copy2(artifact, release_dir / artifact.name)

            subprocess.run(["git", "add", "release"], cwd=temp_path, check=True)
            subprocess.run(["git", "commit", "-m", commit_message], cwd=temp_path, check=True)

            commit_hash = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=temp_path,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()

            subprocess.run(
                [
                    "git",
                    "-C",
                    str(self.project_root),
                    "fetch",
                    str(temp_path),
                    f"{branch_name}:{branch_name}",
                ],
                check=True,
            )

            if tag_name:
                subprocess.run(
                    [
                        "git",
                        "-C",
                        str(self.project_root),
                        "tag",
                        "-a",
                        tag_name,
                        "-m",
                        commit_message,
                        commit_hash,
                    ],
                    check=True,
                )

            if push:
                subprocess.run(
                    ["git", "-C", str(self.project_root), "push", "-u", "origin", branch_name],
                    check=True,
                )
                if tag_name:
                    subprocess.run(
                        ["git", "-C", str(self.project_root), "push", "origin", tag_name],
                        check=True,
                    )

            self.print_success(
                f"Created artifact-only branch '{branch_name}'"
                + (f" with tag '{tag_name}'" if tag_name else "")
            )
        
    def show_build_info(self, exe_path: Path) -> None:
        """Show information about the built executable"""
        self.print_header("BUILD COMPLETED SUCCESSFULLY")
        
        print(f"{Colors.GREEN}{Colors.BOLD}Executable Location:{Colors.END}")
        print(f"  {exe_path}")
        
        # Get file size
        try:
            size_bytes = exe_path.stat().st_size
            size_mb = size_bytes / (1024 * 1024)
            print(f"\n{Colors.BLUE}File Size:{Colors.END} {size_mb:.1f} MB ({size_bytes:,} bytes)")
        except OSError:
            pass
            
        print(f"\n{Colors.BLUE}Build Type:{Colors.END} {self.build_type.title()}")
        print(f"{Colors.BLUE}Platform:{Colors.END} {sys.platform}")
        
        print(f"\n{Colors.YELLOW}To run the executable:{Colors.END}")
        if sys.platform == 'win32':
            print(f"  {exe_path}")
        else:
            print(f"  ./{exe_path.name}  (from {exe_path.parent})")
            
    def build(self, clean: bool = False) -> bool:
        """Main build process"""
        self.print_header(f"INNOMIGHTLABS CLI BUILD ({self.build_type.upper()})")
        
        # Pre-build checks
        if not self.check_python_version():
            return False
            
        if not self.check_spec_file():
            return False
            
        # Clean if requested
        if clean:
            self.cleanup_build_artifacts()
            
        # Install PyInstaller
        if not self.install_pyinstaller():
            return False
            
        # Build the executable
        if not self.build_executable():
            return False
            
        # Find and report the executable
        exe_path = self.find_executable()
        if exe_path:
            self.show_build_info(exe_path)
            return True
        else:
            return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Build script for InnomightLabs CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s                    # Development build (default)
  %(prog)s --dev              # Explicit development build
  %(prog)s --release          # Release build
  %(prog)s --clean            # Clean build artifacts first
  %(prog)s --dev --clean      # Clean development build
  %(prog)s --release --clean  # Clean release build
  %(prog)s --artifact-release --artifact-tag v0.2.0  # Build and create artifact-only tag
'''
    )
    
    # Create mutually exclusive group for build type
    build_type_group = parser.add_mutually_exclusive_group()
    
    build_type_group.add_argument(
        '--dev',
        action='store_true',
        help='Build for development (explicit, with debug info)'
    )
    
    build_type_group.add_argument(
        '--release', 
        action='store_true',
        help='Build for release (optimized, no debug info)'
    )
    
    parser.add_argument(
        '--clean', 
        action='store_true',
        help='Clean build artifacts before building'
    )
    
    parser.add_argument(
        '--clean-only', 
        action='store_true',
        help='Only clean build artifacts, do not build'
    )

    parser.add_argument(
        '--artifact-release',
        action='store_true',
        help='Build and create an artifact-only git branch (and optional tag)'
    )
    parser.add_argument(
        '--artifact-name',
        type=str,
        help='Base name for the generated artifact archive (defaults to timestamped name)'
    )
    parser.add_argument(
        '--artifact-branch',
        type=str,
        help='Name of the orphan branch to create for artifacts (defaults to artifacts/<tag|timestamp>)'
    )
    parser.add_argument(
        '--artifact-tag',
        type=str,
        help='Optional git tag to create that points to the artifact-only commit'
    )
    parser.add_argument(
        '--artifact-message',
        type=str,
        help='Custom commit message for the artifact-only branch'
    )
    parser.add_argument(
        '--push-artifact',
        action='store_true',
        help='Push the artifact branch (and tag) to origin after creation'
    )
    
    args = parser.parse_args()
    
    # Determine build type - defaults to development if neither is specified
    if args.release or args.artifact_release:
        build_type = 'release'
    else:
        build_type = 'development'  # Default to development (covers both --dev and no flag)
    
    
    # Create build manager
    builder = BuildManager(build_type)
    
    # Handle clean-only option
    if args.clean_only:
        builder.print_header("CLEANING BUILD ARTIFACTS")
        builder.cleanup_build_artifacts()
        builder.print_success("Cleanup completed")
        return 0

    if args.artifact_release:
        try:
            success = builder.build(clean=args.clean)
            if not success:
                return 1

            exe_path = builder.find_executable()
            if exe_path is None:
                return 1

            artifact_archive, artifact_checksum = builder.package_artifacts(
                exe_path,
                artifact_name=args.artifact_name,
            )

            builder.create_artifact_only_release(
                artifacts=[artifact_archive, artifact_checksum],
                branch_name=args.artifact_branch,
                tag_name=args.artifact_tag,
                commit_message=args.artifact_message,
                push=args.push_artifact,
            )

            builder.print_success("Artifact release workflow completed")
            return 0
        except KeyboardInterrupt:
            builder.print_warning("\nArtifact release interrupted by user")
            return 1
        except Exception as exc:
            builder.print_error(f"Artifact release failed: {exc}")
            return 1
        
    # Run the build
    try:
        success = builder.build(clean=args.clean)
        return 0 if success else 1
    except KeyboardInterrupt:
        builder.print_warning("\nBuild interrupted by user")
        return 1
    except Exception as e:
        builder.print_error(f"Unexpected error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
