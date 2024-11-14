import re
import gordion

GREEN_CHECK = "\033[32m\u2713\033[0m"


def expand(ifile: str, ofile: str):
  workspace = gordion.Workspace()

  # Define the pattern to match <gordion:path:name> and capture "name" as repo_name
  pattern = r"<gordion:path:(\w+)>"

  # Read the input file
  print(f"Reading {ifile}", end=" ")
  with open(ifile, 'r') as f:
    content = f.read()
  print(GREEN_CHECK)

  # Find all occurrences and store them in a list of tuples (full_match, name)
  matches = re.findall(pattern, content)

  # Process each captured name and replace the corresponding placeholder in the content
  for name in matches:
    repo = workspace.get_repository_or_throw(name)
    content = re.sub(f"<gordion:path:{name}>", repo.path, content)

  # Write the modified content to the output file
  print(f"Writing {ofile}", end=" ")
  with open(ofile, 'w') as f:
    f.write(content)
  print(GREEN_CHECK)
