Some notes regarding the installations of the EHR setup:

- pyROOT is required. So do not forget to install ROOT using python flag:
./configure --enable-python

- To use the new FrontPanel software (I could not find the one I used during the thesis anymore...) on Ubuntu 14 an old package is required.
Get it from:
http://packages.ubuntu.com/precise/libudev0
and then do:
dpkg -i libudev0_175-0ubuntu9_amd64.deb

-The pyDTB software (by Wolfram Erdmann) was used and needs a PyUSB (1.6) software.

-Some python packages will be needed. Most importantly numpy and a dev-pkg. Do:
sudo apt-get install python-dev
sudo apt-get install python-numpy
