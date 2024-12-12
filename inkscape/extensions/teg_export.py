import os
import subprocess
import inkex
from inkex.utils import debug

class TEGGenerateMap(inkex.Effect):
    def __init__(self):
        super().__init__()
        self.input_file = None

    def add_arguments(self, pars):
        pars.add_argument("--layer_file", type=str, help="File with the Layer names")
        pars.add_argument("--output_folder", type=str, help="Target folder for all PNGs")
        pars.add_argument("--tab", type=str, help="UI Tab argument")

    def effect(self):
        self.input_file = self.document_path()
        debug(f"Use document: {self.input_file}")

        layer_file = self.options.layer_file
        output_folder = self.options.output_folder

        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        if not os.path.exists(layer_file):
            debug(f"Layer file {layer_file} not found!")
            return

        try:
            with open(layer_file, 'r') as file:
                layers = [line.strip() for line in file if line.strip()]
        except Exception as e:
            inkex.errormsg(f"Failed to load layer file '{layer_file}': {e}")
            return

        for layer_path in layers:
            debug(f"Processing layer path: {layer_path}")
            try:
                layer = self.find_layer_by_path(layer_path)
                if layer is None:
                    debug(f"Layer not found for path: {layer_path}")
                    continue

                clip_image = self.find_clip_image_by_label("Clip_Image")
                if clip_image is None:
                    debug("Clip image not found. Available labels:")
                    self.debug_all_labels()
                    continue

                self.apply_clipping(layer, clip_image)
                output_file = os.path.join(output_folder, f"{layer_path.replace('/', '_')}.png")
                self.export_to_png(clip_image, output_file)

                self.remove_clipping(clip_image)
            except Exception as e:
                inkex.errormsg(f"Error processing layer '{layer_path}': {e}")

    def find_layer_by_path(self, path):
        groups = path.split("/")
        current_group = self.svg

        for group_name in groups[:-1]:
            current_group = self.find_group(current_group, group_name)
            if current_group is None:
                debug(f"Group '{group_name}' not found.")
                return None

        return self.find_path_by_label(current_group, groups[-1])

    def find_group(self, parent, group_name):
        inkscape_ns = "{http://www.inkscape.org/namespaces/inkscape}"
        for child in parent:
            if child.tag == "{http://www.w3.org/2000/svg}g" and child.get(f"{inkscape_ns}label") == group_name:
                return child
        return None

    def find_path_by_label(self, parent, label):
        inkscape_ns = "{http://www.inkscape.org/namespaces/inkscape}"
        for child in parent:
            if child.tag == "{http://www.w3.org/2000/svg}path" and child.get(f"{inkscape_ns}label") == label:
                return child
        return None

    def find_clip_image_by_label(self, label):
        inkscape_ns = "{http://www.inkscape.org/namespaces/inkscape}"
        for element in self.svg.getiterator():
            element_label = element.get(f"{inkscape_ns}label")
            if element_label:
                debug(f"Checking label: {element_label}")
                if element_label == label:
                    debug(f"Found matching clip image with label: {label}")
                    return element
        debug(f"No matching clip image found for label: {label}")
        return None

    def debug_all_labels(self):
        inkscape_ns = "{http://www.inkscape.org/namespaces/inkscape}"
        for element in self.svg.getiterator():
            label = element.get(f"{inkscape_ns}label")
            if label:
                debug(f"Found label: {label}")

    def apply_clipping(self, layer, clip_image):
        try:
            layer_id = layer.get("id")
            clip_image_id = clip_image.get("id")

            if not layer_id or not clip_image_id:
                debug(f"Invalid IDs: layer_id={layer_id}, clip_image_id={clip_image_id}")
                return
            debug(f"Using input file for subprocess: {self.input_file}")
            debug(f"Clip image visibility: {clip_image.get('style')}")
            debug(f"Layer visibility: {layer.get('style')}")
            debug(f"Clearing selection and applying clipping with IDs: layer_id={layer_id}, clip_image_id={clip_image_id}")

            subprocess.run([
                "inkscape",
                "--actions",
                f"select-clear;select-by-id:{clip_image_id};select-by-id:{layer_id};object-set-clip",
                f"{self.input_file}"
            ], check=True, stderr=subprocess.PIPE)
            debug(f"Clipping applied to layer {layer_id}")
        except subprocess.CalledProcessError as e:
            debug(f"Error during clipping: {e.stderr}")

    def remove_clipping(self, clip_image):
        try:
            clip_image_id = clip_image.get("id")
            if not clip_image_id:
                debug(f"Invalid layer ID for unclipping: {clip_image_id}")
                return

            subprocess.run([
                "inkscape",
                "--actions",
                f"select-clear;select-by-id:{clip_image_id};object-release-clip",
                f"{self.input_file}"
            ], check=True)
            debug(f"Clipping removed from layer {clip_image_id}")
        except subprocess.CalledProcessError as e:
            debug(f"Error during clipping removal: {e.stderr}")

    def export_to_png(self, clip_image, output_file):
        clip_image_id = clip_image.get('id')
        try:
            subprocess.run([
                "inkscape",
                "--actions",
                f"select-clear;select-by-id:{clip_image_id};export-type:png;export-area-drawing;export-filename:{output_file};export-do",
                f"{self.input_file}"
            ], check=True)
            debug(f"Exporting layer ID: {clip_image_id} to file: {output_file}")
        except subprocess.CalledProcessError as e:
            debug(f"Error during PNG export: {e.stderr}")

if __name__ == '__main__':
    TEGGenerateMap().run()
