Key Resource Table Extractor
============================

This project provides several table extraction pipelines for key resource table extraction from biomedical papers in PDF format.

# Installation

## Prerequisites
* Linux or Mac OS 
* Java 1.8
* Gradle 4.10.3 (for building)
* Python 3.9+
* Postgres DB 9+

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

## DB Setup


Using psql

```
create database czi_pdf_table_extractor;
create user czi with encrypted password '';
grant all privileges on database czi_pdf_table_extractor to czi;
```

### Creating the DB schema for the Table Detection and Extraction Server

```
cd $HOME/key_resource_table_extractor/scripts
psql -U czi -d czi_pdf_table_extractor < db_schema.sql
```
## Configuration

Copy the config file in scripts directory named `key_resource_table_extractor.ini.example` to `key_resource_table_extractor.ini` and update it according your environment. The example file is listed below

```
[postgresql]
host=localhost
database=czi_pdf_table_extractor
user=czi
password=<PWD>
[security]
api-key=<API-KEY>
[model]
row-merge-model-dir=<ROW-MERGE-DIR>
[config]
work-dir=<FULL-PATH-TO-KEY-RESOURCE-TABLE-EXTRACTOR-CODE-BASE>
server-cache-dir=<SERVER-OUTPUT-CACHE-DIR>
```
* The API Key is used for destructive (delete) operations on the server.
* `row-merge-model-dir` is the directory where the row merge model finetuned from the Table Language model introduced in our paper is saved and can be retrieved from Figshare soon (pending).
* `work-dir` is the directory where this repository is installed in your system e.g. `$HOME/key_resource_table_extractor`.
* `server-cache-dir` is the directory where the extraction artifacts and intermediate files are stored during processing i.e. `/tmp/cache`.

## Table Detection and Extraction Server

```bash
source $HOME/kr_te_env/bin/activate 
cd $HOME/key_resource_table_extractor/scripts
uvicorn api:app --port 8001
```

## Table Extraction Client

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

