def word_ngrams(input_string: str, n: int) -> set:
    """
    Generates a list of n grams from the input_string, including unigrams, up to n-grams.
    """
    words = input_string.split()
    n_grams = []
    for m in range(1, n + 1):
        n_grams.extend([" ".join(words[i : i + m]) for i in range(len(words) - m + 1)])
    return set(n_grams)
