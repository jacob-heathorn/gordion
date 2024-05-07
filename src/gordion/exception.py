class OperationError(Exception):
  """Exception raised for user facing errors that an operation cannot be performed."""
  def __init__(self, message="Operation error."):
      self.message = message
      super().__init__(self.message)

