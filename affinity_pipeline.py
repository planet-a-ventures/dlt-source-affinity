import dlt
from dlt_source_affinity import ListReference, source

DEV_MODE = True


def load_affinity_data() -> None:
    pipeline = dlt.pipeline(
        pipeline_name="affinity_pipeline", destination="duckdb", dev_mode=DEV_MODE
    )
    data = source(
        list_refs=[
            ListReference(248283),
            ListReference(247888, 1869904),
            ListReference(69224, 351112),
            ListReference(126638, 1133940),
            ListReference(157541, 831583),
        ],
        dev_mode=DEV_MODE,
    )
    if DEV_MODE:
        data.add_limit(1)
    info = pipeline.run(data, refresh="drop_sources")
    print(info)


if __name__ == "__main__":
    load_affinity_data()
