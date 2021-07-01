# MALBoost: a web-based application for Gene Regulatory Network Analysis in *Plasmodium falciparum*

[![MIT License][license-shield]][license-url]


<!-- PROJECT LOGO -->
<br />
<p align="center">
  <a href="https://github.com/roelof89/malboost">
    <img src="static/img/malpar.jpg" alt="Logo" width="150" height="80">
  </a>

  <h3 align="center">MALBoost web application</h3>

  <p align="center">
    Source code behind the MALBoost web applicaiton
    <br />
    
</p>



<!-- TABLE OF CONTENTS -->
<details open="open">
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
      <ul>
        <li><a href="#built-with">Built With</a></li>
      </ul>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
    <li><a href="#acknowledgements">Acknowledgements</a></li>
  </ol>
</details>



<!-- ABOUT THE PROJECT -->
## About The Project

[![Product Name Screen Shot][product-screenshot]](http://malboost.bi.up.ac.za)

MALBoost as web application which allows researchers to construct Gene Regulatory Networks (GRNs) based on the [Arboreto](https://doi.org/10.1093/bioinformatics/bty916) library in python. The web framework constructs GRNs through a supervised approach using either GRNBoost2 or GENIE3.

The application is intended for *Plasmodium spp.* GRN construction, howerver the algorithm is in no way organisms specific.

### Built With

This section should list any major frameworks that you built your project using. Leave any add-ons/plugins for the acknowledgements section. Here are a few examples.
* [Python3](https://www.python.org)
* [Flask](https://flask.palletsprojects.com)
* [Celery - Distributed Task Queue](https://docs.celeryproject.org/en/stable/index.html)
* [Redis](https://redis.io)
* [SQLite](https://www.sqlite.org/index.html)


<!-- GETTING STARTED -->
## Getting Started

The application is built using python-flask, redis and celery worker. The data is stored and managed using SQLite.
It's recommended to use a python virtual environment.

### Prerequisites

This is an example of how to list things you need to use the software and how to install them.
#### Python virtual environment
* python virtual environment
  ```sh
  python3 -m venv env
  source env/bin/activate
  ```

#### Redis
* install redis macOS
  ```sh
  brew install redis
  ```

* install redis linux
  ```sh
    wget http://download.redis.io/redis-stable.tar.gz
    tar xvzf redis-stable.tar.gz
    cd redis-stable
    make
  ```

Please see documentation for [Redis](https://redis.io) more detail

#### SQLite
* install SQLite linux
  ```sh
  sudo apt update
  sudo apt install sqlite3
  ```

### Installation

1. Clone the repo
   ```sh
   git clone https://github.com/your_username_/Project-Name.git
   ```
2. Install python packages
   ```sh
   pip install -r requirements.txt
   ```



<!-- USAGE EXAMPLES -->
## Usage

Use the launch shell script to start the application, this will run redis, celery and then flask.
Check port configurations and nginx for hosting on web.
* create .env file with the following variables
```sh
app_url='http://url:port'
CELERY_BROKER_URL='redis://localhost:6380' # match launch
CELERY_RESULT_BACKEND='redis://localhost:6380'
SQLALCHEMY_DATABASE_URI='sqlite:///data/YOURDATABASE.db'
```

* start app
```sh
./launch.sh
```
* stop app
```sh
./kill.sh
```

<!-- LICENSE -->
## License

Distributed under the MIT License. See `LICENSE` for more information.

<!-- CONTACT -->
## Contact

Your Name - roelofvanwyk89@gmail.com

<!-- ACKNOWLEDGEMENTS -->
## Acknowledgements
* [TUKS: Centre for Bioinformatics and Computational Biology](https://www.up.ac.za/centre-for-bioinformatics-and-computational-biology)
* [Arboreto](https://arboreto.readthedocs.io/en/latest/)
* [Aertslab](https://github.com/aertslab/arboreto)
* [Choose an Open Source License](https://choosealicense.com)
* [GitHub Pages](https://pages.github.com)
* [Bootstrap](https://stackpath.bootstrapcdn.com)

<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
[license-shield]: https://img.shields.io/github/license/othneildrew/Best-README-Template.svg?style=for-the-badge
[license-url]: https://github.com/othneildrew/Best-README-Template/blob/master/LICENSE.txt
[product-screenshot]: static/img/product-sh.png
