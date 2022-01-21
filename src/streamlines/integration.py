# Integrate from given point to produce streamlines
import numpy as np


class Integration:

    def __init__(self, interp):
        self.interp = interp
        self.ppoint = None
        self.cpoint = None

    def compute(self, method='p-space', time_step=1e-6):
        from src.function.variables import Variables
        # TODO add switch case
        if method == 'p-space':
            # For p-space algos; the point -in-domain check was done in search
            if self.interp.idx.ppoint is None:
                self.ppoint = None
                return self.ppoint

            q_interp = Variables(self.interp)
            q_interp.compute_velocity()
            self.ppoint = self.interp.idx.ppoint + q_interp.velocity.reshape(3) * time_step

            return self.ppoint

        if method == 'c-space':
            # Get inverse Jacobian from the interpolation class
            _J_inv = self.interp.idx.grid.m2[self.interp.idx.cell[0, 0], self.interp.idx.cell[0, 1],
                                             self.interp.idx.cell[0, 2], :, :, self.interp.idx.block]

            q_interp = Variables(self.interp)
            q_interp.compute_velocity()
            p_velocity = q_interp.velocity.reshape(3)
            c_velocity = np.matmul(_J_inv, p_velocity)
            self.cpoint = self.interp.idx.cpoint + c_velocity * time_step

            # For c-spce the point in-domain check is done after integration
            if not np.all([0, 0, 0] <= self.cpoint) or not np.all(
                    self.cpoint + 1 < [self.interp.idx.grid.ni[self.interp.idx.block],
                                       self.interp.idx.grid.nj[self.interp.idx.block],
                                       self.interp.idx.grid.nk[self.interp.idx.block]]):
                self.cpoint = None
                return self.cpoint

            return self.cpoint

        if method == 'pRK4':
            from src.streamlines.interpolation import Interpolation
            from src.streamlines.search import Search

            def _rk4_step(self, x):
                idx = Search(self.interp.idx.grid, x)
                idx.compute()
                # For p-space algos; the point-in-domain check was done in search
                if idx.ppoint is None: return None
                interp = Interpolation(self.interp.flow, idx)
                interp.compute()
                q_interp = Variables(interp)
                q_interp.compute_velocity()
                v = q_interp.velocity.reshape(3)
                k = time_step * v
                return k

            # Start RK4 for p-space
            # For p-space algos; the point-in-domain check was done in search
            x0 = self.interp.idx.ppoint
            if x0 is None: return None
            q_interp = Variables(self.interp)
            q_interp.compute_velocity()
            v0 = q_interp.velocity.reshape(3)
            k0 = time_step * v0
            x1 = x0 + 0.5 * k0

            k1 = _rk4_step(self, x1)
            if k1 is None: return None
            x2 = x0 + 0.5 * k1

            k2 = _rk4_step(self, x2)
            if k2 is None: return None
            x3 = x0 + k2

            k3 = _rk4_step(self, x3)
            if k3 is None: return None
            x4 = x0 + 1/6 * (k0 + 2*k1 + 2*k2 + k3)

            self.ppoint = x4

            return self.ppoint

        if method == 'cRK4':
            '''
            This is a block-wise integration. Everytime the point gets out
            a pRK4 is run to find the new block the point is located in.
            That particular step is done in streamlines algorithm.
            
            All the points, x0, x1... are in c-space
            '''
            from src.streamlines.interpolation import Interpolation
            from src.streamlines.search import Search

            def _rk4_step(self, x):
                idx = Search(self.interp.idx.grid, x)
                idx.block = self.interp.idx.block
                idx.c2p(x)  # This will change the cell attribute
                # In-domain check is done in search
                if idx.cpoint is None:
                    self.cpoint = None
                    self.ppoint = None
                    return None
                interp = Interpolation(self.interp.flow, idx)
                interp.compute(method='c-space')
                _J_inv = interp.J_inv
                q_interp = Variables(interp)
                q_interp.compute_velocity()
                p_velocity = q_interp.velocity.reshape(3)
                c_velocity = np.matmul(_J_inv, p_velocity)
                k = time_step * c_velocity
                return k

            x0 = self.interp.idx.cpoint
            _J_inv = self.interp.J_inv
            if x0 is None: return None

            q_interp = Variables(self.interp)
            q_interp.compute_velocity()
            p_velocity = q_interp.velocity.reshape(3)
            c_velocity = np.matmul(_J_inv, p_velocity)
            k0 = time_step * c_velocity
            x1 = x0 + 0.5 * k0

            k1 = _rk4_step(self, x1)
            if k1 is None: return None
            x2 = x0 + 0.5 * k1

            k2 = _rk4_step(self, x2)
            if k2 is None: return None
            x3 = x0 + k2

            k3 = _rk4_step(self, x3)
            if k3 is None: return None
            x4 = x0 + 1/6 * (k0 + 2*k1 + 2*k2 + k3)

            self.cpoint = x4

            return self.cpoint
