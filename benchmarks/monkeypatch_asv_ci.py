# ------------ FIX FOR #45 ------------
# See https://github.com/airspeed-velocity/asv_runner/issues/45
# -------------------------------------

def timeit(self, number):
    """
    Run the function's code `number` times in a separate Python process, and
    return the execution time.

    #### Parameters
    **number** (`int`)
    : The number of times to execute the function's code.

    #### Returns
    **time** (`float`)
    : The time it took to execute the function's code `number` times.

    #### Notes
    The function's code is executed in a separate Python process to avoid
    interference from the parent process. The function can return either a
    single string of code to be executed, or a tuple of two strings: the
    code to be executed and the setup code to be run before timing.
    """
    stmt = self.func()
    if isinstance(stmt, tuple):
        stmt, setup = stmt
    else:
        setup = ""
    stmt = textwrap.dedent(stmt)
    setup = textwrap.dedent(setup)
    stmt = stmt.replace(r'"""', r"\"\"\"")
    setup = setup.replace(r'"""', r"\"\"\"")

    # TODO
    # -----------ORIGINAL CODE-----------
    # code = self.subprocess_tmpl.format(stmt=stmt, setup=setup, number=number)

    # res = subprocess.check_output([sys.executable, "-c", code])
    # return float(res.strip())

    # -----------NEW CODE-----------
    code = self.subprocess_tmpl.format(stmt=stmt, setup=setup, number=number)

    evaler = textwrap.dedent(
        """
        import sys
        code = sys.stdin.read()
        exec(code)
        """
    )

    proc = subprocess.Popen([sys.executable, "-c", evaler],
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    stdout, stderr = proc.communicate(input=code.encode("utf-8"))
    if proc.returncode != 0:
        raise RuntimeError(f"Subprocess failed: {stderr.decode()}")
    return float(stdout.decode("utf-8").strip())

_SeparateProcessTimer.timeit = timeit

# ------------ END FIX #45 ------------
