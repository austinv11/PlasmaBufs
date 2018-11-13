import os
import os.path as osp
import shutil
import sys
from glob import glob
from subprocess import call, Popen, PIPE

"""
Builds python and java bindings for gRPC protobuf services declared in modules in the proto directory.
"""


def module_names(module):
    return module + "_java", module + "_python"


def compile_python(module, loc):
    # Dependencies
    call([sys.executable, "-m", "venv", "venv"])

    with Popen("base" if sys.platform != 'win32' else 'cmd', shell=True, stdin=PIPE, stdout=PIPE, stderr=PIPE,
               encoding='utf8') as p:
        if sys.platform == 'win32':
            cmd = "venv\\Scripts\\activate"
        else:
            cmd = "source activate venv/bin/activate"

        p.stdin.write(cmd + "\n")
        p.stdin.write(sys.executable + ' -m pip install grpcio-tools\n')

        # FIXME
        to_exec = " ".join([sys.executable,
                            "-m",
                            "grpc_tools.protoc",
                            "-I" + osp.join("proto", module),
                            "--python_out=" + loc,
                            "--grpc_python_out=" + loc]
                           + glob(osp.join("proto", module, "*.proto")))

        p.stdin.write(to_exec)

        p.stdin.flush()
        p.communicate()
        p.wait()

    # call(["pip", "install", "googleapis-common-protos"])


GRADLE_TEMPLATE = """
apply plugin: 'java'
apply plugin: 'com.google.protobuf'

repositories {
  maven { url "https://plugins.gradle.org/m2/" }
}

buildscript {
  repositories {
    maven { url "https://plugins.gradle.org/m2/" }
    jcenter()
  }
  dependencies {
    classpath 'com.google.protobuf:protobuf-gradle-plugin:0.8.7'
  }
}

dependencies {
  compile 'com.google.protobuf:protobuf-java:3.0.0'
  compile 'io.grpc:grpc-stub:1.16.1'
  compile 'io.grpc:grpc-protobuf:1.16.1'
  if (JavaVersion.current().isJava9Compatible()) {
    // Workaround for @javax.annotation.Generated
    // see: https://github.com/grpc/grpc-java/issues/3633
    compile 'javax.annotation:javax.annotation-api:1.3.1'
  }

  testCompile 'junit:junit:4.12'
}

protobuf {
  protoc {
    artifact = "com.google.protobuf:protoc:3.5.1-1"
  }
  plugins {
    grpc {
      artifact = 'io.grpc:protoc-gen-grpc-java:1.16.1'
    }
  }
  generateProtoTasks {
    ofSourceSet('main')*.plugins {
      grpc { }
    }
  }
}
"""


def compile_java(module, loc):
    shutil.copy(osp.join("gradle", "gradlew"), osp.join(loc, "gradlew"))
    shutil.copy(osp.join("gradle", "gradlew.bat"), osp.join(loc, "gradlew.bat"))
    os.makedirs(osp.join(loc, "gradle", "wrapper"), exist_ok=True)
    shutil.copy(osp.join("gradle", "gradle-wrapper.properties"),
                osp.join(loc, "gradle", "wrapper", "gradle-wrapper.properties"))
    shutil.copy(osp.join("gradle", "gradle-wrapper.jar"), osp.join(loc, "gradle", "wrapper", "gradle-wrapper.jar"))

    with open(osp.join(loc, "settings.gradle"), 'w') as f:
        f.write("rootProject.name = '{}'".format(loc))

    with open(osp.join(loc, "build.gradle"), 'w') as f:
        f.write(GRADLE_TEMPLATE)

    os.makedirs(osp.join(loc, "src", "main", "proto"))
    for f in glob(osp.join("proto", module, "*.proto")):
        shutil.copy(f, osp.join(loc, "src", "main", "proto", os.path.basename(f)))

    exe = "gradlew.bat" if sys.platform == 'win32' else './gradlew'
    call(exe + " build", cwd=osp.abspath(loc), shell=True)


def build_module(module):
    java, python = module_names(module)

    if osp.exists(java):
        shutil.rmtree(java)
    os.mkdir(java)
    if osp.exists(python):
        shutil.rmtree(python)
    os.mkdir(python)

    compile_java(module, java)
    compile_python(module, python)


def main():
    modules = os.listdir("proto")

    for module in modules:
        print("Building the gRPC submodule '" + module + "'...")
        build_module(module)

    print("Build complete.")


if __name__ == '__main__':
    main()
