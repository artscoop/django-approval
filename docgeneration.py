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
    # Run pdoc on the base directory
    # And generate the HTML docs in the docs directory.
    # The name is made mandatory by Github pages, so one cannot name
    # the folder documentation for example.
    pdoc.pdoc("approval", output_directory=SOURCE_PATH / "docs")

