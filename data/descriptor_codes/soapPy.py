### DEFINE ###
from ctypes import *
import os, argparse
import numpy as np
import genBasis 
import ase, ase.io
import os

def format_ase2clusgeo(obj):
    """ Takes an ase Atoms object and returns numpy arrays and integers
    which are read by the internal clusgeo. Apos is currently a flattened
    out numpy array
    """
    #atoms metadata
    totalAN = len(obj)

    atomtype_set = set(obj.get_atomic_numbers())
    num_atomtypes = len(atomtype_set)

    atomtype_lst = np.sort(list(atomtype_set))
    n_atoms_per_type_lst = []
    pos_lst = []
    for atomtype in atomtype_lst:
        condition = obj.get_atomic_numbers() == atomtype
        pos_onetype = obj.get_positions()[condition]
        n_onetype = pos_onetype.shape[0]

        # store data in lists
        pos_lst.append(pos_onetype)
        n_atoms_per_type_lst.append(n_onetype)

    typeNs = n_atoms_per_type_lst
    Ntypes = len(n_atoms_per_type_lst)
    atomtype_lst
    Apos = np.concatenate(pos_lst).ravel()
    return Apos, typeNs, Ntypes, atomtype_lst, totalAN
    
def format_flp2clusgeo(data):
    """ Takes an ase Atoms object in flp format and returns numpy arrays and integers
    which are read by the internal clusgeo. Apos is currently a flattened
    out numpy array
    """
    #atoms metadata
    totalAN = data.natm

    atomtype_set = set(data.Zs)
    num_atomtypes = len(atomtype_set)

    atomtype_lst = np.sort(list(atomtype_set))
    n_atoms_per_type_lst = []
    pos_lst = []
    for atomtype in atomtype_lst:
        condition = data.Zs == atomtype
        pos_onetype = data.coords[condition]
        n_onetype = pos_onetype.shape[0]

        # store data in lists
        pos_lst.append(pos_onetype)
        n_atoms_per_type_lst.append(n_onetype)

    typeNs = n_atoms_per_type_lst
    Ntypes = len(n_atoms_per_type_lst)
    Apos = np.concatenate(pos_lst).ravel()
    return Apos, typeNs, Ntypes, atomtype_lst, totalAN


def soap(obj, Hpos, rCutHard=8.0, NradBas=5, Lmax=5, atoms_list=None):
    assert Lmax <= 9, "l cannot exceed 9. Lmax={}".format(Lmax) 
    assert Lmax >= 0, "l cannot be negative.Lmax={}".format(Lmax) 
    assert rCutHard < 10.0001 , "hard redius cuttof cannot be larger than 10 Angs. rCut={}".format(rCutHard) 
    assert rCutHard > 4.999 , "hard redius cuttof cannot be lower than 5 Ang. rCut={}".format(rCutHard)
    assert NradBas >= 2 , "number of basis functions cannot be lower than 2. NradBas={}".format(NradBas)
    assert NradBas <= 10 , "number of basis functions cannot exceed 10. NradBas={}".format(NradBas)

    # get clusgeo internal format for c-code
    Apos, typeNs, py_Ntypes, atomtype_lst, totalAN = format_ase2clusgeo(obj)
    # flatten Hpos array
    Hpos = np.array(Hpos)
    py_Hsize = Hpos.shape[0]
    Hpos = Hpos.flatten()
    alp, bet = genBasis.getBasisFunc(rCutHard, NradBas)
    
    #Declaring main soap array, for atoms in atoms_list
    if atoms_list == None:
        atoms_list = atomtype_lst
    soap_nfeature = NradBas**2*(Lmax+1)
    soap = np.zeros((py_Hsize, soap_nfeature*len(atoms_list)))

    # convert int to c_int
    alphas = (c_double*len(alp))(*alp)
    betas = (c_double*len(bet))(*bet)
    l = c_int(Lmax)
    Hsize = c_int(py_Hsize)
    Ntypes = c_int(py_Ntypes)
    totalAN = c_int(totalAN)
    rCutHard = c_double(rCutHard)
    Nsize = c_int(NradBas)
    #convert int array to c_int array
    typeNs = (c_int * len(typeNs))(*typeNs)

    #print(l, Hsize, Ntypes, totalAN, typeNs, Nsize)
    # convert to c_double arrays
    #Apos
    axyz = (c_double * len(Apos))(*Apos.tolist())
    #Hpos
    hxyz = (c_double * len(Hpos))(*Hpos.tolist())

    ### START SOAP###
    dir_ = os.path.dirname(__file__)
    filename = ''.join([dir_, '/src/libsoapPy.so'])
    libsoap = CDLL(filename)
    libsoap.soap.argtypes = [POINTER (c_double),POINTER (c_double), POINTER (c_double),POINTER (c_double),POINTER (c_double), POINTER (c_int),c_double,c_int,c_int,c_int,c_int,c_int]
    libsoap.soap.restype = POINTER (c_double)
    # double* c, double* Apos,double* Hpos,int* typeNs,
    # int totalAN,int Ntypes,int Nsize, int l, int Hsize);
    c = (c_double*(soap_nfeature*py_Ntypes*py_Hsize))()
    c = libsoap.soap( c, axyz, hxyz, alphas, betas, typeNs, rCutHard, totalAN, Ntypes, Nsize, l, Hsize)
    #   return c;
    soap_part = np.ctypeslib.as_array( c, shape=(py_Hsize,soap_nfeature*py_Ntypes))
    
    for i in range(py_Hsize):
        for j_ind, j in enumerate(atoms_list):
            if j in atomtype_lst:
                j_ind_part = atomtype_lst.tolist().index(j)
                soap[i, soap_nfeature*j_ind:soap_nfeature*(j_ind+1)] = soap_part[i, soap_nfeature*j_ind_part:soap_nfeature*(j_ind_part+1)]
    return soap
    
    
