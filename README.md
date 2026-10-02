# If you can't run snuffler, run this:
`conda install matplotlib==3.8.4` and make sure not to ever update matplotlib

# PyGIMLi Installation Guide

This guide explains **how to correctly install PyGIMLi**, how to fix
common installation errors, and how to install **Tetgen**, which PyGIMLi
needs for 3D mesh generation if an error message occurs.

------------------------------------------------------------------------

# 1. What You Need Before Starting

## ✔️ Install Miniconda (recommended)

If you do not already have Conda installed:

1.  Go to: https://docs.conda.io/en/latest/miniconda.html\
2.  Download the installer for your system:
    -   macOS (Intel or M1/M2/M3)
    -   Linux (e.g., Rocky Linux)
    -   Windows (PyGIMLi support is limited --- use macOS/Linux if
        possible)
3.  Run the installer.
4.  Restart your terminal afterwards.

------------------------------------------------------------------------

# 2. Create a Clean Conda Environment for PyGIMLi

We will create a new environment called **pg**.

### 👉 In your terminal, copy and paste the following command:

    conda create -n pg -c gimli -c conda-forge "pygimli>=1.5.0" python=3.10 suitesparse=5

### Then activate it:

    conda activate pg

If this command finishes **without errors**, PyGIMLi is installed ---\
**BUT you are not done yet!**\
There are usually some issues we must fix manually.

------------------------------------------------------------------------

# 3. Common Issue: PyGIMLi Fails to Import (UMFPACK / CHOLMOD)

Many users encounter this error:

    ImportError: libumfpack.5.dylib not found

or similar errors for:

-   `libumfpack`
-   `libcholmod`

This happens because PyGIMLi expects **older versions** of certain
SuiteSparse libraries, but Conda installs newer ones.

## How to Fix It (macOS + Linux)

1.  Make sure your `pg` environment is activated:

        conda activate pg

2.  Find the environment's library folder.

    Typical locations:

    -   macOS Intel:\
        `~/miniconda3/envs/pg/lib`
    -   macOS M1/M2:\
        `~/miniconda3/envs/pg/lib`
    -   Linux:\
        `~/miniconda3/envs/pg/lib`

3.  Open the folder in your terminal:

        cd ~/miniconda3/envs/pg/lib

4.  List available UMFPACK versions:

        ls -l libumfpack.*.dylib

    You will see something like:

        libumfpack.6.0.1.dylib

5.  Create a symbolic link (shortcut) with the name PyGIMLi expects:

    Example:

        ln -s libumfpack.6.0.1.dylib libumfpack.5.dylib

6.  Do the same for **CHOLMOD**:


        ls -l libcholmod.*.dylib

    Then link:

        ln -s libcholmod.6.0.1.dylib libcholmod.5.dylib

    After this, try:

        python3 -c "import pygimli; print('PyGIMLi works!')"

------------------------------------------------------------------------

# 4. Matplotlib "get_cmap" Error (Optional Fix)

If you see an error like:

    Module matplotlib.cm has no attribute get_cmap

Fix it by installing an older Matplotlib version:

    pip install matplotlib==3.7.3

------------------------------------------------------------------------

# 5. Installing Tetgen (VERY IMPORTANT for 3D work)

PyGIMLi calls **Tetgen** as an external program.\
⚠️ Installing the Python package `tetgen` **does NOT install the
executable** PyGIMLi needs.

So we must install the Tetgen **executable** manually.

------------------------------------------------------------------------

## Step-by-Step Tetgen Installation

Make sure you are **in the pg environment**:

    conda activate pg

### ✔️ Step 1 --- Download Tetgen source code:

    cd /tmp
    wget http://wias-berlin.de/software/tetgen/1.5/src/tetgen1.6.0.tar.gz

### ✔️ Step 2 --- Extract the files:

    tar -xzf tetgen1.6.0.tar.gz
    cd tetgen1.6.0

### ✔️ Step 3 --- Compile Tetgen:

    make

This creates an executable file called `tetgen`.

### ✔️ Step 4 --- Install Tetgen **into your conda environment**

    Copy the executable into the environment's `bin/` folder:

        cp tetgen ~/miniconda3/envs/pg/bin/

### ✔️ Step 5 --- Test Tetgen

    which tetgen

You should see something like:

    /Users/yourname/miniconda3/envs/pg/bin/tetgen

Now test the executable:

    tetgen -h

If the help message appears, Tetgen is correctly installed.

------------------------------------------------------------------------

# 6. Test Your Installation

Start Python:

    python

Then run this code:

    import pygimli
    import pygimli.meshtools as mt

    print("PyGIMLi is working!")

    # Try creating a simple mesh (requires Tetgen)
    world = mt.createWorld(start=[0,0], end=[10,5])
    mesh = mt.createMesh(world)

If no error appears, **everything is working** 🎉

------------------------------------------------------------------------

# 7. Summary of What You Did

1.  Installed Conda
2.  Created a safe environment for PyGIMLi
3.  Installed PyGIMLi + fixed library issues
4.  Fixed Matplotlib if needed
5.  Installed the Tetgen executable
6.  Verified everything works

You are now ready to run modeling and inversion notebooks.

------------------------------------------------------------------------

# Troubleshooting

### If PyGIMLi still refuses to import:

-   Double-check the symbolic links for UMFPACK/CHOLMOD
-   Make sure you performed the steps **inside the pg environment**

### If Tetgen is not found:

-   Make sure the executable was copied to the correct `bin/` folder
-   Run:

        echo $PATH

and verify it includes your conda environment.

------------------------------------------------------------------------
