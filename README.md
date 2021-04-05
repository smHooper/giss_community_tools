

<!-- PROJECT LOGO -->
<br />
<p align="center">
  <a href="https://github.com/smHooper/giss_community_tools">
    <img src="resources/images/logo.png" alt="Logo" width="200" height="200">
  </a>

  <h2 align="center">Community GISS Tools</h2>

  <p align="center">
    Python tools for Geographic Information System Specialists for wildfire response
    <br />
    <br />
    <a href="https://github.com/smHooper/giss_community_tools/issues">Report a bug</a>
    ·
    <a href="https://github.com/smHooper/giss_community_tools/issues">Request a new feature/tool</a>
  </p>
</p>



<!-- TABLE OF CONTENTS -->
<details open="open">
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about">About the project</a>
    </li>
    <li><a href="#requirements">Requirements</a></li>
    <li><a href="#installation">Installation</a></li>
    <li><a href="#usage">Usage</a>
      <ul>
        <li><a href="#using-in-arcgis-pro">In ArcGIS Pro</a></li>
        <li><a href="#using-from-the-command-line">From the command line</a></li>
      </ul>
    </li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
    <li><a href="#acknowledgements">Acknowledgements</a></li>
  </ol>
</details>



<!-- ABOUT THE PROJECT -->
## About

**Community GISS Tools** is a Python Toolbox for ArcGIS for GISSs to automate common workflows for wildfire incidents. Currently available tools are divided into 3 categories:

#### Standard tools
Standard tools have all been tested to run in the currently recommended version of ArcGIS Pro and are actively maintained. These tools include 
* Calculate Geometry Attributes
* [Calculate Containment](https://github.com/smHooper/giss_community_tools/blob/main/docs/CalculateContainment.md)
* Incident Period Backup
* [RoboCopy Archive](https://github.com/smHooper/giss_community_tools/blob/main/docs/RoboCopyArchive.md)
* Fire Progression

#### Beta tools
Beta tools provide automation for additional functionality or workflows not available in the standard tools. 
* _no beta tools available yet_ 

#### Legacy tools
There are also other [legacy tools](https://github.com/smHooper/giss_community_tools/tree/main/legacy_tools) that have not been tested with currently recommended version of ArcGIS Pro. 
<br><br>
*** Note that all tools, including those in the standard toolbox, are all available _as is_ without any guarantee. Always backup your data and projects before modifying them, and use these tools at your own risk. (see [license](#license) for more information)


<!-- GETTING STARTED -->
## Requirements

The only requirement to use the **Community GISS Tools** is **ArcGIS Pro 2.7**. These tools might work in other versions of ArcGIS Pro or ArcGIS Desktop, but they have not been tested and you are discouraged from using them in these software environments.

## Installation

1. [Download the tools](https://github.com/smHooper/giss_community_tools/archive/refs/heads/main.zip).
2. Unzip the file (named **giss_community_tools-main.zip**)
3. Copy the unzipped files into the **tools** folder of your incident's directory



<!-- USAGE EXAMPLES -->
## Usage

#### Using in ArcGIS Pro
From a **Catalog** window, expand the **community_giss_toolbox.pyt** toolbox (or community_giss_toolbox_beta.pyt to use [Beta tools](#beta-tools)) and open the tool of your choice. For usage of each tool, see the [documentation](https://github.com/smHooper/giss_community_tools/tree/main/docs).

#### Using from the command line
All tools in the Standard toolbox can be run from the command line if you have a Python environment with `arcpy` installed. See [ESRI's documentation](https://pro.arcgis.com/en/pro-app/latest/arcpy/get-started/using-conda-with-arcgis-pro.htm) on running standalone scripts or if you're using an independent Anaconda installation, [create your own ArcPy environment](https://gis.stackexchange.com/a/202704). Tools can be run with the following example command
```
python giss_community_toolbox.pyt <tool_class_name> <tool_argument1> <tool_argument2>...
```  
Example:
```
python giss_community_toolbox.pyt RoboCopyArchive c:\path\to\incident\root c:\path\to\target\archive\folder
``` 
To get generic help run <br>
```python giss_community_toolbox.pyt -h```  
or <br>
```python giss_community_toolbox.pyt --help``` 

Note that some arguments for running tools from the command line are slightly different than parameters in the tools GUI dialog in ArcGIS Pro. For instance, `CalculateGeometryAttribtes` accepts the EPSG numeric code for the incident spatial reference rather than the tool dialog's direct reference to a Spatial Reference object. To get detailed information on input parameters and other information, run <br>
```python giss_community_toolbox.pyt <tool_class_name> -h``` 
or <br>
```python giss_community_toolbox.pyt <tool_class_name> --help``` 
to get argument info.



<!-- CONTRIBUTING -->
## Contributing

We _gladly accept_ contributions for new tools, new features, and bug fixes from the GISS community (hence the name of the project!). To contribute:

1. Fork the project
2. Create your feature branch with an informative name (`git checkout -b feature/cool-feature` )
3. Commit your changes (`git commit -m 'Add some cool-feature'`)
4. Push to the branch (`git push origin feature/cool-feature`)
5. Open a pull request

All new tools should be added to the [Beta toolbox](https://github.com/smHooper/giss_community_tools/blob/main/community_giss_toolbox_beta.pyt). With time and discussion among users and contributors, beta tools can be moved to the Standard toolbox. [Submit an issue](https://github.com/smHooper/giss_community_tools/issues) if you would like a tool in the Beta toolbox to be considered for the Standard toolbox.


<!-- LICENSE -->
## License

The **GISS Community Tools** are distributed under the Apache License 2.0 license. All tools are made available _as is_ without any warranty or guarantee. Use them at your own risk. See [LICENSE](https://github.com/smHooper/giss_community_tools/blob/main/LICENSE) for more details. 



<!-- CONTACT -->
## Contact

Sam Hooper - sam_hooper@firenet.gov<br>
Walker Henry - walker_henry@firenet.gov

Project Link: [https://github.com/smHooper/giss_community_tools](https://github.com/smHooper/giss_community_tools)



<!-- ACKNOWLEDGEMENTS -->
## Acknowledgements
* Most **Community GISS Tools** were originally developed by Carl Beyerhelm. The GISS community owes a huge thanks to Carl for all of his efforts!
