---
description: dlt source for affinity.co
keywords: [Affinity API, affinity.co, CRM]
---

# dlt-source-affinity

[DLT](htps://www.github.com/dlt-hub/dlt) source for [Affinity](https://www.affinity.co/).

> If you don't know DLT but stumbled across this when trying to search if you can
> get your data out of Affinity somehow: this will do it - it basically allows
> you to pull mostly any (except some enriched) data out of your Affinity instance
> and into a different [target system (Snowflake, Postgres, etc.) that is supported
> by DLT](https://dlthub.com/docs/dlt-ecosystem/destinations/).

## Usage

Create a `.dlt/secrets.toml` with your [API key](https://support.affinity.co/s/article/How-to-obtain-your-Affinity-API-key):

```toml
affinity_api_key="<YOUR_API_KEY>"
```

and then run the default source with optional list references:

```py
from dlt_source_affinity import ListReference, source as affinity_source

pipeline = dlt.pipeline(
   pipeline_name="affinity_pipeline",
   destination="duckdb",
   dev_mode=True,
)
affinity_data = affinity_source(
   # By default the data source loads:
   # - organizations
   # - persons
   # - lists
   # - opportunities
   # - notes
   # And then we can optionally pass an arbitrary number of lists and list views:
   list_refs=[
      # Loads a list with ID 123,
      # e.g. https://<your-subdomain>.affinity.co/lists/123/
      ListReference(123),
      # Loads a view with ID 456 in list 123,
      # e.g. https://<your-subdomain>.affinity.co/lists/123/views/456-all-organizations
      ListReference(247888, 1869904),
   ]
)
pipeline.run(affinity_data)
```

## Resources

Resources that can be loaded using this verified source are:

| Name                                                              | Description                                         | API version | [Permissions](https://developer.affinity.co/#section/Getting-Started/Permissions) needed |
| -- | -- | -- | -- |
| [companies](https://developer.affinity.co/#tag/companies)         | The stored companies                                | V2          | Requires the "Export All Organizations directory" permission.                            |
| [persons](https://developer.affinity.co/#tag/persons)             | The stored persons                                  | V2          | Requires the "Export All People directory" permission.                                   |
| [opportunities](https://developer.affinity.co/#tag/opportunities) | The stored opportunities                            | V2          | Requires the "Export data from Lists" permission.                                        |
| [lists](https://developer.affinity.co/#tag/lists)                 | A given list and/or a saved view of a list          | V2          | Requires the "Export data from Lists" permission.                                        |
| [notes](https://api-docs.affinity.co/#notes)                      | Notes attached to companies, persons, opportunities | Legacy      | n/a                                                                                      |

## V1 vs V2

There are two versions of the Affinity API:

1. [Legacy](https://api-docs.affinity.co/) which is available for all plans.
2. [V2](https://developer.affinity.co/) which is only available for customers
   with an enterprise plan.

This verified source makes use of both API endpoints.
The authentication credentials for both APIs are the same, however,
they [differ in their authentication behavior](https://support.affinity.co/s/article/How-to-obtain-your-Affinity-API-key#h_01HMF147N699N2V6A9KPFMSBR6).

## Initialize the pipeline

```bash
dlt init affinity duckdb
```

Here, we chose duckdb as the destination. Alternatively, you can also choose redshift,
bigquery, or any of the other [destinations](https://dlthub.com/docs/dlt-ecosystem/destinations/).

## Add credentials

1. You'll need to [obtain your API key](https://support.affinity.co/s/article/How-to-obtain-your-Affinity-API-key)
   and configure the pipeline with it.

## Development

This project is using [devenv](https://devenv.sh/).

### Run the sample

```sh
AFFINITY_API_KEY=[...] python affinity_pipeline.py
```

### Regenerate V2 model

Run

```sh
generate-model
```
