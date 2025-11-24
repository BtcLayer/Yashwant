from setuptools import setup, find_packages

setup(
    name="metastackerbandit",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "numpy>=2.3.4",
        "pandas==2.2.2",
        "joblib>=1.5.2",
        "gspread==6.0.0",
        "google-auth==2.27.0",
        "python-binance==1.0.19",
        "aiohttp==3.9.5",
        "scikit-learn>=1.7.2",
        "scipy>=1.16.2",
        "requests==2.32.3",
    ],
)
