"""Terminal-UI-Helfer (direkt aus v6 uebernommen)."""


def banner(text, width=68, char='='):
    print('\n' + char * width)
    print(f'  {text}')
    print(char * width)


def section(text, width=68):
    print('\n' + '-' * width)
    print(f'  {text}')
    print('-' * width)


def ok(text):   print(f'  [OK]  {text}')
def info(text): print(f'  [..]  {text}')
def warn(text): print(f'  [!!]  {text}')
def err(text):  print(f'  [XX]  {text}')
def step(text): print(f'\n  [>>]  {text}', flush=True)


def ask_yes_no(prompt):
    while True:
        ans = input(f'  {prompt} (j/n): ').strip().lower()
        if ans in ('j', 'n'):
            return ans == 'j'
        err("Bitte 'j' oder 'n' eingeben.")


def ask_int(prompt, lo, hi, default=None):
    while True:
        hint = f' [Standard: {default}]' if default is not None else ''
        raw = input(f'  {prompt}{hint}: ').strip()
        if raw == '' and default is not None:
            return default
        try:
            val = int(raw)
            if lo <= val <= hi:
                return val
            err(f'Bitte eine Zahl zwischen {lo} und {hi} eingeben.')
        except ValueError:
            err('Bitte eine ganze Zahl eingeben.')


def ask_float(prompt, lo, hi, default=None):
    while True:
        hint = f' [Standard: {default}]' if default is not None else ''
        raw = input(f'  {prompt}{hint}: ').strip()
        if raw == '' and default is not None:
            return float(default)
        try:
            val = float(raw)
            if lo <= val <= hi:
                return val
            err(f'Bitte eine Zahl zwischen {lo} und {hi} eingeben.')
        except ValueError:
            err('Bitte eine Dezimalzahl eingeben.')


def ask_path(prompt, default=None):
    hint = f'\n  [Standard: {default}]' if default else ''
    raw = input(f'  {prompt}{hint}\n  Pfad: ').strip()
    return raw if raw else default
