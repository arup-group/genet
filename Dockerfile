FROM mambaorg/micromamba:1.5.3-bullseye-slim

COPY --chown=$MAMBA_USER:$MAMBA_USER . ./src

RUN micromamba install -y -n base -c conda-forge -c city-modelling-lab python=3.11 "proj>=9.3" pip coin-or-cbc --file src/requirements/base.txt && \
    micromamba clean --all --yes
ARG MAMBA_DOCKERFILE_ACTIVATE=1

RUN pip install --no-deps ./src

ENTRYPOINT ["/usr/local/bin/_entrypoint.sh"]