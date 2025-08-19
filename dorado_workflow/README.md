A snakemake workflow for basecalling nanopore reads using dorado.

To use, first create a list of pod5 files, for example:

```bash
$ ls /path/to/pod5s/*.pod5 >pod5_sample_list.txt
```
Then run this workflow using pixi+snakemake:

```bash
$ /work/microbiome/sw/pixi/latest/.pixi/bin/pixi run --frozen --manifest-path /work/microbiome/sw/hpc_scripts/dorado_workflow/pixi.toml snakemake --snakefile ~/git/hpc_scripts/dorado_workflow/Snakefile --config pod5_sample_list=pod5_sample_list.txt --profile aqua
```

There are several parameters you can adjust by specifying other configuration options in the `--config` argument. See the `Snakefile` for available options. The parameters and software versions used are output in the `cmr_dorado_output/parameters.yaml` file.

Improvements for the future:
* Add input list of barcodes to keep
* Make running it a bit more user-friendly, e.g. by adding a script to run it
