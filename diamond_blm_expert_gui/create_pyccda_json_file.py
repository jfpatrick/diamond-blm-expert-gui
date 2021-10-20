########################################################
########################################################

# GUI created by: martinja
# Contact: javier.martinez.samblas@cern.ch

########################################################
########################################################

# IMPORTS

import pyccda
import pprint
import json
import os

########################################################
########################################################

# GLOBALS

QUERY = '((global==false) and (deviceClassInfo.name=="BLMDIAMONDVFC") and (timingDomain=="LHC" or timingDomain=="SPS")) or (name=="*dBLM.TEST*")'

########################################################
########################################################

# this function retrieves the list of devices and their property-field names for a given query
def create_pyccda_json_file(query = QUERY, name_json_file = "pyccda_sps.json", verbose = False):

    # the query instructions are here:
    # https://gitlab.cern.ch/controls-configuration-service/controls-configuration-data-api/accsoft-ccs-ccda/-/blob/dev/accsoft-ccs-pyccda/generator/docs/generate_query_ref.py
    # and the device-query-related instructions here:
    # https://gitlab.cern.ch/controls-configuration-service/controls-configuration-data-api/accsoft-ccs-ccda/-/blob/dev/accsoft-ccs-ccda-client-domain/src/main/java/cern/accsoft/ccs/ccda/client/model/device/query/DeviceQueryField.java

    # instantiate the api
    api = pyccda.SyncAPI()

    # search the devices
    device_list = api.Device().search(query)

    # create the output dictionary
    output_dict = {}

    # iterate over all devices
    for device in device_list:

        # create the accelerator dictionary
        if device.accelerator_name not in output_dict:
            output_dict[device.accelerator_name] = {}

        # get the property info
        fesa_class_property = api.FesaClassProperty().find(device.device_class_info)

        # create the device dictionary
        dict_device_info = {}
        dict_device_info["acquisition"] = {}
        dict_device_info["command"] = {}
        dict_device_info["setting"] = {}
        dict_device_info["cycle_bound"] = ""

        # check cycle bound (e.g. LHC devices usually have no cycle data)
        if device.is_cycle_bound:
            dict_device_info["cycle_bound"] = "True"
        else:
            dict_device_info["cycle_bound"] = "False"

        # iterate over all properties
        for property in fesa_class_property:

            # determine if the property type
            if property.sub_scope == "acquisition":
                property_type = "acquisition"
            elif property.sub_scope == "setting":
                if property.property_fields:
                    property_type = "setting"
                else:
                    property_type = "command"

            # ignore non-subscribable weird cases (e.g. DiagnosticSetting)
            if not property.is_subscribable and property_type != "command":
                continue

            # create the property dictionary
            dict_device_info[property_type][property.name] = {}
            dict_device_info[property_type][property.name]["array"] = {}
            dict_device_info[property_type][property.name]["scalar"] = {}
            dict_device_info[property_type][property.name]["other"] = {}
            dict_device_info[property_type][property.name]["mux"] = ""

            # check if the property is multiplexed
            if property.is_multiplexed:
                dict_device_info[property_type][property.name]["mux"] = "True"
            else:
                dict_device_info[property_type][property.name]["mux"] = "False"

            # iterate over all fields
            for field in property.property_fields:

                # check if field makes sense
                if field.primitive_data_type != None:

                    # ignore common fields such as acqStamp or cycleStamp
                    if field.name not in ["acqStamp", "cycleStamp", "cycleName"]:

                        # determine field type
                        if field.item_type == "scalar":
                            field_type = "scalar"
                        elif field.item_type == "array":
                            field_type = "array"
                        else:
                            field_type = "other"

                        # add the field to the dictionary
                        dict_device_info[property_type][property.name][field_type][field.name] = {}

        # save the dictionary
        output_dict[device.accelerator_name][device.name] = dict_device_info

    # print the output dictionary
    if verbose:
        pprint.pprint(output_dict)

    # create the saving dir in case it does not exist
    if not os.path.exists("aux_jsons"):
        os.mkdir("aux_jsons")

    # store the json file
    with open("aux_jsons/{}".format(name_json_file), 'w') as fp:
        json.dump(output_dict, fp, sort_keys=True, indent=4)

    return output_dict

########################################################
########################################################

# main
if __name__ == '__main__':

    # call the function
    output_dict = create_pyccda_json_file()

########################################################
########################################################