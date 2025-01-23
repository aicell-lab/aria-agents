import setuptools
import subprocess

class AriaInstallCommand(setuptools.Command):
    description = 'Custom installation steps'
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        # Create and activate the Conda environment
        subprocess.check_call(['conda', 'create', '-n', 'aria-agents', 'python=3.10.13', '-y'])
        subprocess.check_call(['conda', 'activate', 'aria-agents'])

        # Install dependencies
        subprocess.check_call(['pip', 'install', '-r', 'requirements_test.txt'])
        subprocess.check_call(['pip', 'install', '-e', '.'])

        # Prompt the user for the OpenAI API key
        api_key = input("Please enter your OpenAI API key: ")

        # Create the .env file with the provided API key
        with open('aria_agents/.env', 'w', encoding="utf-8") as file:
            file.write(f"OPENAI_API_KEY={api_key}\n")

        print("Setup complete. The OpenAI API key has been saved to aria_agents/.env.")

# Read dependencies from requirements.txt
with open("requirements.txt", encoding="utf-8") as f:
    requirements = f.read().splitlines()

setuptools.setup(
    name="aria-agents",
    version="0.1",
    install_requires=requirements,
    cmdclass={
        'install': AriaInstallCommand,
    },
)