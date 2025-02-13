import re
import gordion
import os


def generate_pyproject_toml(package: str):
  """
  Recursively expands <gordion:pyproject:repo/path/to/package> environment variables in
  package/*.in.toml file and generates *.toml output file.
  """

  # If the package does not contain pyproject.in.toml, return.
  ifile = os.path.join(package, 'pyproject.in.toml')
  if not os.path.isfile(ifile):
    return

  # Set ofile to ifile without the '.in' part
  ofile = ifile.replace('.in.toml', '.toml')

  workspace = gordion.Workspace()

  # Define the pattern to match <gordion:pyproject:repo/path/to/package>.
  pattern = r"<gordion:pyproject:(\w+)(/[^>]+)>"

  # Read the input file
  print(f"Reading {ifile}.")
  with open(ifile, 'r') as f:
    content = f.read()

  # Process each match
  def replacer(match):
    name = match.group(1)             # Captures "name"
    path_to_package = match.group(2)  # Captures /path/to/package
    repo = workspace.get_repository_or_throw(name)
    # Replace gordion:path:name with repo.path and keep the subpath
    subpackage = f"{repo.path}{path_to_package}"

    # Recurse into subpackage path.
    generate_pyproject_toml(subpackage)

    # Return subpackage
    return subpackage

  # Replace all matches
  content = re.sub(pattern, replacer, content)

  # Read output file if it exists.
  if os.path.isfile(ofile):
    with open(ofile, 'r') as f:
      existing_content = f.read()
      if existing_content == content:
        print("No changes necessary.")
        return

  # Write the modified content to the output file
  print(f"Writing {ofile}.")
  with open(ofile, 'w') as f:
    f.write(content)
