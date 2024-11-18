import re
import gordion
import os


def expand(ifile: str, ofile: str):
  """
  Expands <gordion:> environment variables from the input file and generates the output file.
  """
  workspace = gordion.Workspace()

  # Define the pattern to match <gordion:path:name> and capture "name" as repo_name
  pattern = r"<gordion:path:(\w+)>"

  # Read the input file
  print(f"Reading {ifile}.")
  with open(ifile, 'r') as f:
    content = f.read()

  # Find all occurrences and store them in a list of tuples (full_match, name)
  matches = re.findall(pattern, content)

  # Process each captured name and replace the corresponding placeholder in the content
  for name in matches:
    repo = workspace.get_repository_or_throw(name)
    content = re.sub(f"<gordion:path:{name}>", repo.path, content)

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
