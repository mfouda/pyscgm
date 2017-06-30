import numpy as np
from scipy import linalg


def approx_range_finder(A, size, n_iter, piter_normalizer='auto',
                        rgen=np.random):
    """Computes an orthonormal matrix whose range approximates the range of A.

    Parameters
    ----------
    A: numpy matrix
        The input data matrix

    size: integer
        Size of the return array

    n_iter: integer
        Number of power iterations used to stabilize the result

    piter_normalizer: 'auto' (default), 'QR', 'LU', 'none'
        Whether the power iterations are normalized with step-by-step
        QR factorization (the slowest but most accurate), 'none'
        (the fastest but numerically unstable when `n_iter` is large, e.g.
        typically 5 or larger), or 'LU' factorization (numerically stable
        but can lose slightly in accuracy). The 'auto' mode applies no
        normalization if `n_iter`<=2 and switches to LU otherwise.

    rgen: RandomState
        A random number generator instance

    Returns
    -------
    Q: numpy matrix
        A (A.shape[0] x size) projection matrix, the range of which
        approximates well the range of the input matrix A.

    Notes
    -----

    Follows Algorithm 4.3/4.4 of
    Finding structure with randomness: Stochastic algorithms for constructing
    approximate matrix decompositions
    Halko, et al., 2009 (arXiv:909) http://arxiv.org/pdf/0909.4061

    An implementation of a randomized algorithm for principal component
    analysis
    A. Szlam et al. 2014

    Original implementation from scikit-learn.

    """
    A = np.asmatrix(A)

    # Generating normal random vectors with shape: (A.shape[1], size)
    # note that real normal vectors are sufficient, no complex values necessary
    Q = rgen.randn(A.shape[1], size)

    # Deal with "auto" mode
    if piter_normalizer == 'auto':
        if n_iter <= 2:
            piter_normalizer = 'none'
        else:
            piter_normalizer = 'LU'

    # Perform power iterations with Q to further 'imprint' the top
    # singular vectors of A in Q
    for i in range(n_iter):
        if piter_normalizer == 'none':
            Q = A * Q
            Q = A.H * Q
        elif piter_normalizer == 'LU':
            Q, _ = linalg.lu(A * Q, permute_l=True)
            Q, _ = linalg.lu(A.H * Q, permute_l=True)
        elif piter_normalizer == 'QR':
            Q, _ = linalg.qr(A * Q, mode='economic')
            Q, _ = linalg.qr(A.H * Q, mode='economic')

    # Sample the range of A using by linear projection of Q
    # Extract an orthonormal basis
    Q, _ = linalg.qr(A * Q, mode='economic')
    return np.asmatrix(Q)


def randomized_svd(M, n_components, n_oversamples=10, n_iter='auto',
                   piter_normalizer='auto', transpose='auto',
                   rgen=np.random):
    """Computes a truncated randomized SVD

    Parameters
    ----------
    M: numpy matrix or sparse matrix
        Matrix to decompose

    n_components: int
        Number of singular values and vectors to extract.

    n_oversamples: int (default is 10)
        Additional number of random vectors to sample the range of M so as
        to ensure proper conditioning. The total number of random vectors
        used to find the range of M is n_components + n_oversamples. Smaller
        number can improve speed but can negatively impact the quality of
        approximation of singular vectors and singular values.

    n_iter: int or 'auto' (default is 'auto')
        Number of power iterations. It can be used to deal with very noisy
        problems. When 'auto', it is set to 4, unless `n_components` is small
        (< .1 * min(X.shape)) `n_iter` in which case is set to 7.
        This improves precision with few components.

    piter_normalizer: 'auto' (default), 'QR', 'LU', 'none'
        Whether the power iterations are normalized with step-by-step
        QR factorization (the slowest but most accurate), 'none'
        (the fastest but numerically unstable when `n_iter` is large, e.g.
        typically 5 or larger), or 'LU' factorization (numerically stable
        but can lose slightly in accuracy). The 'auto' mode applies no
        normalization if `n_iter`<=2 and switches to LU otherwise.

    transpose: True, False or 'auto' (default)
        Whether the algorithm should be applied to M.T instead of M. The
        result should approximately be the same. The 'auto' mode will
        trigger the transposition if M.shape[1] > M.shape[0] since this
        implementation of randomized SVD tend to be a little faster in that
        case.

    random_state: RandomState
        A random number generator instance to make behavior

    Notes
    -----
    This algorithm finds a (usually very good) approximate truncated
    singular value decomposition using randomization to speed up the
    computations. It is particularly fast on large matrices on which
    you wish to extract only a small number of components. In order to
    obtain further speed up, `n_iter` can be set <=2 (at the cost of
    loss of precision).

    References
    ----------
    * Finding structure with randomness: Stochastic algorithms for constructing
      approximate matrix decompositions
      Halko, et al., 2009 http://arxiv.org/abs/arXiv:0909.4061

    * A randomized algorithm for the decomposition of matrices
      Per-Gunnar Martinsson, Vladimir Rokhlin and Mark Tygert

    * An implementation of a randomized algorithm for principal component
      analysis
      A. Szlam et al. 2014
    """
    M = np.asmatrix(M)
    sketch_size = n_components + n_oversamples

    if n_iter == 'auto':
        # Checks if the number of iterations is explicitely specified
        # Adjust n_iter. 7 was found a good compromise for PCA.
        n_iter = 7 if n_components < .1 * min(M.shape) else 4

    if transpose == 'auto':
        transpose = M.shape[0] < M.shape[1]
    if transpose:
        M = M.T

    Q = approx_range_finder(M, sketch_size, n_iter, piter_normalizer, rgen)
    # project M to the (k + p) dimensional space using the basis vectors
    B = Q.H * M

    # compute the SVD on the thin matrix: (k + p) wide
    Uhat, s, V = linalg.svd(B, full_matrices=False)
    del B
    U = np.dot(Q, Uhat)

    if transpose:
        # transpose back the results according to the input convention
        return (np.asmatrix(V[:n_components, :]).T, s[:n_components],
                np.asmatrix(U[:, :n_components]).conj())
    else:
        return (np.asmatrix(U[:, :n_components]), s[:n_components],
                np.asmatrix(V[:n_components, :]).H)
