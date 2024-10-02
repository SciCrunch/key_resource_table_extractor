Key Resource Table Extractor
============================

This projects provides several table extraction pipelines for key resource table extraction from biomedical papers in PDF format.

# Installation

## Prerequisites
* Linux or Mac OS 
* Java 1.8
* Gradle 4.10.3 (for building)
* Python 3.9+

## Getting the code
```bash
cd $HOME
git clone https://<username>@github.com/SciCrunch/key_resource_table_extractor.git
cd $HOME/key_resource_table_extractor/scripts
```

## Python setup

Create a Python virtual environment

```bash
python3 -m venv ~/kr_te_venv
```
Install the requirements to your newly created environment

```bash
source ~/kr_te_env/bin/activate
cd $HOME/key_resource_table_extractor/scripts
pip install -r requirements.txt
```

# Table Detection and Extraction Server

```bash
source $HOME/kr_te_env/bin/activate 
cd $HOME/key_resource_table_extractor/scripts
uvicorn api:app --port 8001
```

# Table Extraction Client

```bash
source $HOME/kr_te_env/bin/activate
cd $HOME/key_resource_table_extractor/scripts
python test_client.py --help
```

For convenience set the root directory of papers in PDF document to be processed 

```bash
python test_client.py set-root <YOUR-PDF-ROOT-DIRECTORY>
```

After that you can submit jobs to the key resource extraction server by specifying relative (to the root directory) path for the PDF document.

```bash
python test_client.py submit -p <PDF-relative-path>
```

To get more help for a test client command

```bash
python test_client.py submit --help
```

