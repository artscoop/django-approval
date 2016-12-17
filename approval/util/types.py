# coding: utf-8
import math

from django.db.models.base import Model
from django.db.models.query import QuerySet


SI_PREFIXES = ['', 'k', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y']


# Arithmétique
def subtract(value, amount):
    """ Soustraire """
    return value - amount


def delta(value, amount):
    """
    Renvoyer le cardinal de la soustraction

    :returns: la valeur positive de la différence entre value et amount
    """
    return abs(value - amount)


def round_multiple(x, base=1):
    """
    Renvoyer le multiple de *base* le plus proche de *x**

    :param base: un multiple de cette valeur doit être renvoyé
    :param x: nombre à arrondir
    :type base: float | int
    ex. :
    round_multiple(0, 25) == 0
    round_multiple(12, 25) == 0
    round_multiple(13, 25) == 25
    round_multiple(-12, 25) == 0

    """
    return (base * round(float(x) / base)) if type(base) in {int, float} and base > 0 else None


def modulo(value, br):
    """
    Renvoyer un modulo ou comparer un modulo

    :param value: valeur
    :param br: int, float ou chaîne de 2 nombres b et r séparés par une virgule
    :returns: value % br si br est un nombre, sinon renvoie si value % b est égal à r
    """
    try:
        if isinstance(br, str) and "," in br:
            b, r = br.split(",")
            return float(r) - 0.000000001 <= value % float(b) <= float(r) + 0.000000001
        else:
            b = float(br)
            if b > 0:
                result = value % b
                return result
    except ValueError:
        pass
    return False


def to_percent(value, ratio=None):
    """
    Convertir une valeur en pourcentage

    :param ratio: définit quelle valeur de `value` correspond à 100%. 1.0 par défaut
    :type ratio: int | float
    """
    return (value * 100.0) / (float(ratio or 1))


def si_prefix(value):
    """
    Renvoyer une représentation d'un nombre avec les unités du système international

    Ex. 234 567 renvoie 234k, 123 567 890 renvoie 123M
    """
    level = math.floor(math.log(value, 1000))
    unit_count = int(value / (1000 ** level))
    return "{count:d}{unit}".format(count=unit_count, unit=SI_PREFIXES[int(level)])


def invert(value):
    """ Renvoyer le contraire d'un booléen """
    return not value


def percent_status(value, asc=True):
    """ Renvoyer un statut de santé depuis un flottant entre 0 et 100 """
    if asc is True:
        if value < 33.33:
            return 'success'
        elif value < 66.67:
            return 'warning'
        else:
            return 'danger'
    else:
        if value > 66.67:
            return 'success'
        elif value > 33.33:
            return 'warning'
        else:
            return 'danger'


def nestedsort(value, item_index=0):
    """ Trier un tuple de tuples en utilisant l'élément de tuple d'index *item_index* """
    try:
        item_index = int(item_index)
        value.sort(key=lambda item: item[item_index])
        return value
    except ValueError:
        return value


def model_name(value):
    """ Renvoyer le nom du modèle de l'objet """
    if isinstance(value, Model):
        return value._meta.verbose_name
    return None


def str_to(value, newtype, default=0):
    """ Renvoyer une chaîne convertie en un autre type ou une valeur par défaut (0) """
    try:
        return newtype(value)
    except ValueError:
        return default


def string_to_dict(options):
    """
    Convertir une chaîne d'options k=v en dictionnaire

    :param options: chaîne du type 'a1 a2=v2 a3=v3'
    """
    output = dict()
    tokens = (options or '').split()
    for token in tokens:
        if token.strip():
            if '=' in token:
                arg, value = token.split('=')
                output[arg] = value
            else:
                output[token] = True
    return output


def make_iterable(value, output_type=list):
    """
    Renvoyer un type d'itérable depuis un objet seul ou un itérable

    Renvoie un itérable vide si value est None
    """
    if type(value) is output_type:
        return value
    if isinstance(value, (list, set, tuple, QuerySet)) and type(value) != output_type:
        return output_type(value)
    return output_type([value]) if value is not None else output_type()


def list_contains(t, text):
    """ Renvoyer si un itérable de chaînes contient une sous-chaîne """
    for i in t:
        if text in i:
            return True
    return False


def is_multi_dimensional(value):
    """ Renvoyer si une liste ou un tuple contient des listes ou des tuples """
    if isinstance(value, (list, tuple)) and value:
        return isinstance(value[0], (list, tuple))
    return False
