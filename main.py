from Application import Application

# Start the application only when this file is executed directly.
if __name__ == "__main__":
    try:
        Application().run()
    except RuntimeError as error:
        # Report application and recovery failures without a misleading success message.
        raise SystemExit(str(error)) from error