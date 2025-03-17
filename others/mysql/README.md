# Build instructions for MySQL Server 8.0.39

## Get the files

```
wget https://github.com/mysql/mysql-server/archive/refs/tags/mysql-8.0.39.tar.gz
tar -xzf mysql-8.0.39.tar.gz
cd mysql-server-mysql-8.0.39
```

## Patch

Note that when MySQL is built with TSan, it uses a lower optimization level (or no optimization) than a build without TSan.
You may want to change this depending on your experiment needs.

You may change the optimization level for builds with TSan by applying the patch below.

```diff
1110,1111c1110,1111
<       STRING_APPEND(CMAKE_C_FLAGS   " -O1 -fno-inline")
<       STRING_APPEND(CMAKE_CXX_FLAGS " -O1 -fno-inline")
---
>       # STRING_APPEND(CMAKE_C_FLAGS   " -O1 -fno-inline")
>       # STRING_APPEND(CMAKE_CXX_FLAGS " -O1 -fno-inline")
```

## Dependencies

Below are instructions for building the dependencies from source. Building from source is mainly just to make this guide more portable.

Nonetheless, if you just want to get them from the package manager, here is the command for Ubuntu 24.04.

```sh
sudo apt install -y build-essential make bison libssl-dev libudev-dev libtirpc-dev pkg-config
```

## Dependencies for the dependencies

At least, you still need the basic build tools (`make`, `cmake` etc). Here is the command for getting them via the package manager in Ubuntu 24.04.

```sh
sudo apt install -y build-essential make m4 cmake
```

## Build

Download and build the dependencies in a `downloads` folder in the `mysql-server-8.0.39`

