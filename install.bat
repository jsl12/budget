CALL .\venv\Scripts\activate.bat
pip install -e .
jupyter nbextension enable --py --sys-prefix widgetsnbextension
jupyter nbextension enable --py --sys-prefix qgrid
