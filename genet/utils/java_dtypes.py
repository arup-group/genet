JAVA_DTYPE_MAP = {
    "java.lang.Array": list,
    "java.lang.Boolean": bool,
    "java.lang.Double": float,
    "java.lang.Float": float,
    "java.lang.Long": float,
    "java.lang.Integer": int,
    "java.lang.Byte": int,
    "java.lang.Short": int,
    "java.lang.Char": str,
    "java.lang.String": str,
}

PYTHON_DTYPE_MAP = {
    list: "java.lang.Array",
    set: "java.lang.Array",
    bool: "java.lang.Boolean",
    float: "java.lang.Float",
    int: "java.lang.Integer",
    str: "java.lang.String",
}


def java_to_python_dtype(java_dtype: str) -> type:
    if java_dtype in JAVA_DTYPE_MAP:
        return JAVA_DTYPE_MAP[java_dtype]
    else:
        raise NotImplementedError(
            f"Java type: {java_dtype} is not understood. The following Java data types are "
            f"supported: {list(JAVA_DTYPE_MAP)}"
        )


def python_to_java_dtype(python_dtype: type) -> str:
    if python_dtype in PYTHON_DTYPE_MAP:
        return PYTHON_DTYPE_MAP[python_dtype]
    else:
        raise NotImplementedError(
            f"Python type: {python_dtype} is not recognised or implemented to be mapped to a "
            f"Java type. The following types are supported: {list(PYTHON_DTYPE_MAP)}"
        )
