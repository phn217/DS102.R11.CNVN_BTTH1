# f(x, y) = x^4 + y^2 + 2xy + 1
import numpy as np

def f(u):
    x, y = u
    return x**4 + y**2 + 2 * x * y + 1

def grad(u):
    x, y = u
    return np.array([4 * x**3 + 2 * y,
                     2 * y + 2 * x])

def hessian(u):
    x, y = u
    return np.array([[12 * x**2, 2],
                     [2, 2]])

def newton_optimizer(grad_fn, hessian_fn, u0, tol=1e-8, max_iter=100):
    u = np.asarray(u0, dtype=float).copy()
    history = [u.copy()]

    for _ in range(max_iter):
        g = grad_fn(u)
        if np.linalg.norm(g) <= tol:
            return np.array(history), u, True

        H = hessian_fn(u)
        try:
            step = np.linalg.solve(H, g)
        except np.linalg.LinAlgError:
            return np.array(history), u, False

        u = u - step
        history.append(u.copy()) 
    return np.array(history), u, np.linalg.norm(grad_fn(u)) <= tol

#Phân loại điểm dừng theo trị riêng của Hessian
def classify(hessian_fn, u, eps=1e-10):
    w = np.linalg.eigvalsh(hessian_fn(u))
    if np.all(w > eps):
        return "cực tiểu địa phương"
    if np.all(w < -eps):
        return "cực đại địa phương"
    if np.any(w > eps) and np.any(w < -eps):
        return "điểm yên ngựa"
    return "không kết luận được (Hessian suy biến)"

if __name__ == "__main__":
    for u0 in [(10, 10), (-3, 2), (0.3, 0.1), (-0.3, 0.1)]:
        hist, u, ok = newton_optimizer(grad, hessian, u0)
        print(f"u0={u0}: u*={u}, f={f(u):.6f}, "
              f"{len(hist)-1} bước, hội tụ={ok}, loại: {classify(hessian, u)}")