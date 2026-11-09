# Start the application and report dependency or runtime failures clearly.
if __name__ == "__main__":
    try:
        # Import inside the protected block so dependency errors can be handled.
        from Application import Application
        # Start the normal application workflow.
        Application().run()
    except ModuleNotFoundError as error:
        # Identify a missing external package or project module.
        raise SystemExit(f"Startup failed: required module '{error.name}' was not found.\nEnsure all project files are present and dependencies from python_dependencies.txt are installed.\nFor Docker, rebuild the image with: docker compose build quantifresh") from error
    except ImportError as error:
        # Explain failures involving unavailable imported names or incompatible modules.
        raise SystemExit(f"Application import failed: {error}\nCheck the import names, module locations and dependency versions.") from error
    except RuntimeError as error:
        # Report application and recovery errors without displaying a success message.
        raise SystemExit(str(error)) from error