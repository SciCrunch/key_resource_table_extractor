from configparser import ConfigParser


def config(filename="key_resource_table_extractor.ini", section='postgresql'):
    parser = ConfigParser()
    parser.read(filename)

    db = {}
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            db[param[0]] = param[1]
    else:
        raise Exception('Section {0} not found in the {1} file'.format(section, filename))
    return db


def get_api_key(filename="key_resource_table_extractor.ini"):
    section = 'security'
    parser = ConfigParser()
    parser.read(filename)
    if parser.has_section(section):
        return parser.get(section, 'api-key')
    else:
        raise Exception('Section {0} not found in the {1} file'.format(section, filename))


def get_rm_model_dir(filename="key_resource_table_extractor.ini"):
    section = "model"
    parser = ConfigParser()
    parser.read(filename)
    if parser.has_section(section):
        return parser.get(section, 'row-merge-model-dir')
    else:
        raise Exception('Section {0} not found in the {1} file'.format(section, filename))
