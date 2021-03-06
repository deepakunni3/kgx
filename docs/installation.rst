Installation
============

The installation for requires Python 3.7 or greater.

Installation for users
----------------------

First clone the GitHub repository and then install,

.. code-block:: bash

    git clone https://github.com/NCATS-Tangerine/kgx
    cd kgx
    python setup.py install


Installation for developers
---------------------------


To build directly from source, first clone the GitHub repository,

.. code-block:: bash

    git clone https://github.com/NCATS-Tangerine/kgx
    cd kgx


Then install the necessary dependencies listed in ``requirements.txt``.

.. code-block:: bash

    pip3 install -r requirements.txt



For convenience, make use of the ``venv`` module in Python 3 to create a lightweight virtual environment:

.. code-block:: bash

   python3 -m venv env
   source env/bin/activate

   pip install -r requirements.txt
