"""Run the whole pipeline end to end:  python src/run_pipeline.py"""
import generate_data  # noqa: F401  (runs on import: writes data/raw/*.csv)
import ingest, quality_checks, clean, olap_queries, benchmark, make_report

if __name__ == "__main__":
    ingest.main()
    quality_checks.main("raw")      # BEFORE cleaning
    clean.main()
    quality_checks.main("clean")    # AFTER cleaning
    olap_queries.main()
    benchmark.main()
    make_report.main()
    print("\nPipeline complete. See the reports/ folder.")
