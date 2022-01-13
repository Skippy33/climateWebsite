# Define base image
FROM continuumio/miniconda3
LABEL tag="climate_website"
# Set working directory for the project
WORKDIR /app
EXPOSE 5000
# Create Conda environment from the YAML file
COPY environment.yml .
COPY templates templates
COPY static static

RUN conda env create -f environment.yml
 
# Override default shell and use bash
SHELL ["conda", "run", "-n", "env", "/bin/bash", "-c"]
 
# Activate Conda environment and check if it is working properly
RUN echo "Making sure flask is installed correctly..."
RUN python -c "import flask"
 
# Python program to run in the container
COPY main.py .
ENTRYPOINT ["conda", "run", "-n", "env", "python", "main.py"]