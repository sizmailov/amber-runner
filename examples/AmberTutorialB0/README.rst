
.. image:: http://ambermd.org/tutorials/basic/tutorial0/include/Alanine_Dipeptide_3D.png

This is implementation of `AMBER Tutorial B0 <http://ambermd.org/tutorials/basic/tutorial0/>`_  using
``amber-runner`` library.

The whole MD protocol and analysis are described in ``init.py``. Here we set up
sequence of steps to perform. Protocol serialized as ``./B0/state.dill``

The ``run_*.py`` script loads MD protocol from ``./B0/state.dill``
and runs it step by step. Interrupted script can
be safely started again. It will continue from latest unfinished MD step.

.. code-block::


    ## describe md protocol and serialize it
    python init.py

    ## run simulation on local machine
    python run_locally.py

    ## or run on local PBS server
    # python run_on_local_pbs_server.py

    ## or run on remote machine via ssh
    # python run_remotely.py





