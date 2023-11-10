import sys
from os import environ
from pathlib import Path
import django
import pdoc

if __name__ == '__main__':
    # Configure environment to let Django work
    SOURCE_PATH = Path(__file__).parent
    sys.path.append(str(SOURCE_PATH))
    environ.setdefault("DJANGO_SETTINGS_MODULE", "scenario.settings")
    # Setup Django machinery to load models etc.
    django.setup()
    # Reun pdoc on the base directory
    pdoc.pdoc("approval", output_directory=SOURCE_PATH / "documentation")

