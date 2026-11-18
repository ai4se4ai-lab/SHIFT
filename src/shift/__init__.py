import warnings

# ast.parse of historical sources emits SyntaxWarning for old escape sequences; irrelevant here.
warnings.filterwarnings("ignore", category=SyntaxWarning)
