
def _get_resource_file(filename):
    """ Get resource file path from package
    syntax: python >= 3.7
    """
    import importlib.resources as impresources
    return str(impresources.files('martpy.resources').joinpath(filename))