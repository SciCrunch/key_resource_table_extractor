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
* `row-merge-model-dir` is the directory where the row merge model finetuned from the Table Language model introduced in our paper is saved and can be retrieved from Zenodo soon (pending).
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

# Data

## Data for the Evaluation of Resource Table Extraction Pipelines

The annotated gold standard key resource tables from April 2024 BioRxiv preprints are included in `data/table_content_extract/gs_bioarxiv_extracted_key_resources_tables_sampled` directory.

The raw JSON outputs for the four pipeline introduced in our paper and GROBID baseline are also included under `data/bundle` directory.

* `bioarxiv_extracted_key_resources_tables_sampled` - contains tables extracted by pipeline A (colum info only)
* `extracted_key_resources_tables_with_row_info_sampled_v2` - contains tables extracted by pipeline B (both column and row info)
* `bioarxiv_extracted_key_resources_tables_sampled_ocr` - contains tables extracted by pipeline C (only image level + OCR)
* `bioarxiv_main_merged` - contains tables extracted by pipeline D (pipeline A + Table LM based row merger)
* `sampled_pdfs_grobid_tables` - contains tables extracted by GROBID


The raw outputs need to be converted before being compared against the gold standard via GriTS metric which can be accomplished via the following script for pipeline A for example. Use `-h` option to get more help.

```bash
python table_extractor2_table_json_converter.py -c col_only

```

After that, to get the GriTS score, use `grits_perf_eval.py` script


```bash
python grits_perf_eval.py -c col_only

```

## Data for Training and Evaluation of Key Resource Page Detection Classifier

The annotated documents for key resource page candidate detection ensemble classifier are located in `data/table_detection/annotated` and `data/table_detection_v2/annotated` directories.


The first level deep learning model of the stack generalizer is trained via the `classifier.py` script.

```bash
python classifier.py -c train

```

The second level classifier is a SVM and can be trained via the script `stacked_gen.py`.

```bash
python stacked_gen.py -c train
```

Before training, the training and testing data needs to be prepared using

```bash
python classifier.py -c stack-gen-prep
```

A larger curated set for evaluation is available under the directory `data/rrid_papers_sample_200_03_07_2023`.


