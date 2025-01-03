import os
import subprocess
import inkex
import re
from inkex.utils import Y, debug
from pydoc import parentname

class TEGGenerateMap(inkex.Effect):
    def __init__(self):
        super().__init__()
        self.input_file = None

    def add_arguments(self, pars):
        pars.add_argument("--layer_file", type=str, help="File with the Layer names")
        pars.add_argument("--output_folder", type=str, help="Target folder for all PNGs")
        pars.add_argument("--tab", type=str, help="UI Tab argument")

    def effect(self):
        input_file = self.document_path()
        layer_file = self.options.layer_file
        output_folder = self.options.output_folder

        debug(f"Use document: {input_file}")

        if not os.path.exists(layer_file):
            debug(f"Layer file {layer_file} not found!")
            return

        try:
            with open(layer_file, 'r') as file:
                layers = [line.strip() for line in file if line.strip()]
        except Exception as e:
            inkex.errormsg(f"Failed to load layer file '{layer_file}': {e}")
            return

        if not os.path.exists(output_folder):
            debug(f"Create folder: {output_folder}")
            os.makedirs(output_folder)

        # TODO: Change hardcoded label for clipping image
        clip_image = self.find_clip_image_by_label("Clip_Image")
        if clip_image is None:
            debug("Clip image not found. Available labels:")
            self.debug_all_labels()

        for layer_path in layers:
            debug(f"Processing layer path: {layer_path}")
            try:
                layer = self.find_layer_by_path(layer_path)
                if layer is None:
                    debug(f"Layer not found for path: {layer_path}")
                    continue

                continent_name = layer_path.rsplit("/", 2)[-2]
                country_name = layer_path.rsplit("/", 1)[-1]
                file_name = f"{continent_name}_{country_name}.png"
                debug(f"Filename: {file_name}")
                # Note layer position
                pos_x, pos_y, army_x, army_y = self.element_position(layer)
                if pos_x is not None and pos_y is not None:
                    with open(f"{output_folder}/positions.txt", "a") as file:
                        file.write(f'<country name="{country_name}" file="{file_name}" pos_x="{pos_x}" pos_y="{pos_y}" army_x="{army_x}" army_y="{army_y}"/>\n')
                else:
                    debug(f"Skipping position record for layer: {layer_path}. Position unknown.")

                # Clip it
                output_file = os.path.join(output_folder, file_name)
                self.apply_clip_and_export(input_file, layer, clip_image, output_file)

            except Exception as e:
                inkex.errormsg(f"Error processing layer '{layer_path}': {e}")

    def apply_clip_and_export(self, input_file, layer, clip_image, output_file):
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

            action_clip = (
                f"select-clear;"
                f"select-by-id:{layer_id};"
                f"select-by-id:{clip_image_id};"
                "object-set-clip"
            )
            action_export = (
                f"select-clear;select-by-id:{clip_image_id};"
                "export-type:png;"
                "export-area-drawing;"
                f"export-filename:{output_file};"
                "export-do"
            )
            action_release_clip = (
                f"select-clear;select-by-id:{clip_image_id};"
                "object-release-clip"
            )
            actions = f"{action_clip};{action_export};{action_release_clip}"
            result = subprocess.run(
                ["inkscape", f"{input_file}", "--actions", f"{actions}"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            debug(f"Subprocess success: {result.stdout}")
        except subprocess.CalledProcessError as e:
            debug(f"Error during subprocess call: {e.stderr}")
            raise


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

    # TODO: Use this a stemplate for Root_of_map/Continent
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

    def element_position(self, element):
        # Ensure the element is valid and has an ID
        element_id = element.get("id")
        if element is None:
            debug(f"No matching element with ID '{element_id}' found")
            return None, None, None, None  # Return None if the element isn't found

        # Retrieve the bounding box attributes
        bounding_box = element.bounding_box()
        if bounding_box:
            return round(bounding_box.left), round(bounding_box.top), 0, 0
        else:
            debug(f"No attributes found: {element}. Assuming position (0, 0).")
            return 0, 0, 0, 0


    def debug_all_labels(self):
        inkscape_ns = "{http://www.inkscape.org/namespaces/inkscape}"
        for element in self.svg.getiterator():
            label = element.get(f"{inkscape_ns}label")
            if label:
                debug(f"Found label: {label}")


if __name__ == '__main__':
    TEGGenerateMap().run()
