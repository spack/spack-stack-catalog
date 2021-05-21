spack:
  definitions:
  - compilers: [{{ compiler }}]
  - mpis: [{{ mpi }}]
  - targets: [target={% if arch is defined and arch != None %}{{ arch }}{% else %}{{ arch_family }}{% endif %}]
  - packages: 
      - seissol-env+mpi+asagi~building_tools
      - seissol-utils+cross_arch_build
 
  specs:
  - matrix:
    - [\$compilers]
    - [arch={{ arch_family }}]
  - matrix:
    - [\$mpis, cmake@3.16.2{% if gpu is defined and gpu != None %}, {{ gpu }}{% endif %}]
    - [\$targets]
    - [\$%compilers]
  - matrix:
    - [\$packages]
    - [\$targets]
    - [\$^mpis]
    - [\$%compilers]
  
  container:
    format: docker

    images:
      build: {{ builder_image }}
      final: {{ target_image }}

    {%- if gpu is defined and gpu != None %}
    strip: false
    {%- else %}
    strip: true
    {% endif %}

    os_packages:
      command: {{ install_command }}
      final:
      - python3
      - python3-dev
      - python3-pip
      - pkg-config
      - make
      - git
      - gdb
      - vim

    extra_instructions:
        build: |
            RUN cd /opt/spack-environment && . /opt/spack/share/spack/setup-env.sh \
            && spack env activate --sh -d . >> /opt/spack-environment/seissol_env.sh \
            && spack find -v > /opt/spack-environment/installed_packages.txt 
            {%- if gpu is defined and gpu != None %}
            {%- if 'cuda' in gpu %}
            RUN cuda_real_path=$(dirname $(dirname $(readlink /opt/view/bin/nvcc))) \
            && (echo "export CUDA_PATH=${cuda_real_path}" \
            &&  echo "export CUDA_HOME=${cuda_real_path}" \
            &&  echo "export CMAKE_PREFIX_PATH=\$CMAKE_PREFIX_PATH:${cuda_real_path}" \
            &&  echo "export LD_LIBRARY_PATH=\$LD_LIBRARY_PATH:${cuda_real_path}/lib64/stubs" \
            &&  echo "export LIBRARY_PATH=\$LIBRARY_PATH:${cuda_real_path}/lib64/stubs") >> /opt/spack-environment/cuda_env.sh
            {%- endif %}
            {%- endif %}

        final: |
            RUN update-alternatives --install /usr/bin/python python /usr/bin/python3 20 \
            && compiler_path=$(cat /opt/software/compiler_path | tr -d '\n') \
            && update-alternatives --install /usr/bin/gcc gcc $compiler_path/bin/gcc 20 \
            && update-alternatives --install /usr/bin/g++ g++ $compiler_path/bin/g++ 20 \
            && update-alternatives --install /usr/bin/gfortran gfortran $compiler_path/bin/gfortran 20 \
            && ranlib $compiler_path/lib/gcc/*/*/libgcc.a \
            && pip3 install --upgrade cython wheel \
            && pip3 install scons numpy \
            && mkdir /workspace /usr_mount
