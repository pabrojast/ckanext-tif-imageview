from os import read
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from six import text_type
from flask import Blueprint, request, jsonify
import ckan.lib.helpers as h
import rasterio
from rasterio.io import MemoryFile
import io
import ckan.lib.uploader as uploader
import base64
import requests
from PIL import Image

ignore_empty = plugins.toolkit.get_validator('ignore_empty')

def convert(): 
    
    resource_id = request.form.get('resource_id')    
    rsc = toolkit.get_action('resource_show')({}, {'id': resource_id})
    upload = uploader.get_resource_uploader(rsc)

    def is_valid_domain(url):
        return url.startswith('https://data.dev-wins.com') or url.startswith('https://ihp-wins.unesco.org/')
    print(rsc)
    print(rsc["url"])
    if is_valid_domain(rsc["url"]):
        print('valid domain')
        upload = uploader.get_resource_uploader(rsc)
        filepath = upload.get_url_from_filename(resource_id, rsc['url'])
    else:
        print("not valid domain")
        filepath = rsc["url"]

    try:
        if filepath.startswith('http'):
            print("start with http")
            print(filepath)
            response = requests.get(filepath)
            print(response)
            response.raise_for_status()
            file = response.content
        else:
            print("else")
            with open(filepath, "rb") as f:
                file = f.read()
        
        with MemoryFile(file) as memfile:
            with memfile.open() as dataset:
                data = dataset.read()
                img = Image.fromarray(data[0])  # Suponiendo que solo necesitas la primera banda
                output = io.BytesIO()
                img.convert('RGB').save(output, 'JPEG')
                output.seek(0)
                return base64.b64encode(output.getvalue()).decode()
    except Exception as e:
        return jsonify({"error": str(e)}), 500

class TifImageviewPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IResourceView, inherit=True)
    plugins.implements(plugins.IBlueprint)

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'theme/templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'tif_imageview')
        self.formats = config_.get(
            'ckan.preview.image_formats',
            'tiff tif TIFF').split()

    def info(self):
        return {'name': 'tif_imageview',
            'title': plugins.toolkit._('TIF Viewer'),
            'schema': {'tif_url': [ignore_empty, text_type]},
            'iframed': False,
            'icon': 'link',
            'always_available': True,
            'default_title': plugins.toolkit._('TIF Viewer'),
        }
    
    def can_view(self, data_dict):
        resource = data_dict['resource']
        return (resource.get('format', '').lower() in ['tif', 'tiff'] or
                resource['url'].split('.')[-1] in ['tif'])

    def view_template(self, context, data_dict):
        return 'tif_view.html'

    def form_template(self, context, data_dict):
        return 'tif_form.html'

    def get_blueprint(self):
        blueprint = Blueprint(self.name, self.__module__)
        blueprint.template_folder = u'templates'
        blueprint.add_url_rule(
            u'/tif_view/convert',
            u'convert',
            convert,
            methods=['POST']
            )
        return blueprint