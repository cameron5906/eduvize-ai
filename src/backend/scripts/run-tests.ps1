# Check the platform
if ($PSVersionTable.OS -like "*Linux*") {
    # Linux
    $env:PYTHONPATH = "."
    pytest -v --disable-warnings
}
else {
    # Windows
    $env:PYTHONPATH = "."
    pytest -v --disable-warnings
}
