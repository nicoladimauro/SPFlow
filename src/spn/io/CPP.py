'''
Created on March 22, 2018

@author: Alejandro Molina
'''
import subprocess

from spn.algorithms import Inference
from spn.io.Text import str_to_spn, to_str_equation
from spn.leaves import Histograms
from spn.leaves.Histograms import Histogram, Histogram_Likelihoods
from spn.structure.Base import get_node_by_type, Product, Sum
import numpy as np


def to_cpp(node, feature_names):
    vartype = "double"

    parms = "int i, %s data[][%s]" % (vartype, len(node.scope))
    funcbody = "return " + to_str_equation(node, {
        # Product : lambda node,y,z: "(" + " + ".join(map(lambda child: to_str_equation(child, y, z), node.children)) + ")",

        # Sum: lambda node, y, z: "(log(" + " + ".join(
        #   map(lambda i: str(node.weights[i]) + "*exp(" + to_str_equation(node.children[i], y, z) + ")",
        #      range(len(node.children)))) + "))",

        Histograms.Histogram: lambda node, y, z: "leaf_hist_%s(data[i][%s])" % (id(node), node.scope[0])
    })

    histassignments = ""
    leavefuncs = ""
    for h in get_node_by_type(node, Histogram):
        inps = np.arange(int(max(h.breaks))).reshape((-1, 1))
        ll = Histograms.Likelihood(h, inps)
        hfun = "%s hist_%s[%s];\n" % (vartype, id(h), len(inps))

        ll = np.exp(ll)

        for x, v in enumerate(ll):
            histassignments += "\thist_%s[%s] = %s;\n" % (id(h), x, v)
        histassignments += "\n"

        x = feature_names[h.scope[0]]
        hfun += "inline %s leaf_hist_%s(uint8_t %s){\n" % (vartype, id(h), x)
        hfun += "   return hist_%s[%s]; \n}\n" % (id(h), x)
        leavefuncs += "\n" + hfun

    return """
#include <iostream>
#include <string>
#include <vector>
#include <boost/algorithm/string.hpp>
#include <boost/lexical_cast.hpp>
#include <iomanip>
#include <chrono>


using namespace std;

%s

%s likelihood(%s){
    %s;
}

int main() 
{
%s 
    vector<string> lines;
    for (string line; getline(std::cin, line);) {
        lines.push_back( line );
    }
    
    int n = lines.size()-1;
    int f = %s;
    %s data[n][%s];
    
    for(int i=0; i < n; i++){
        std::vector<std::string> strs;
        boost::split(strs, lines[i+1], boost::is_any_of(";"));
        
        for(int j=0; j < f; j++){
            data[i][j] = boost::lexical_cast<long double>(strs[j]);
        }
    }
    
    %s result[n];
    
    chrono::high_resolution_clock::time_point begin = chrono::high_resolution_clock::now();
    for(int j=0; j < 10000; j++){
        for(int i=0; i < n; i++){
            result[i] = likelihood(i, data);
        }
    }
    chrono::high_resolution_clock::time_point end = chrono::high_resolution_clock::now();

    long double avglikelihood = 0;
    for(int i=0; i < n; i++){
        avglikelihood += log(result[i]);
        //cout << setprecision(15) << log(result[i]) << endl;
    }

    cout << setprecision(15) << "avg ll " << avglikelihood/n << endl;
    
    cout << (chrono::duration_cast<chrono::nanoseconds>(end-begin).count()/1000)  / 10000 << "us" << endl;
    cout << "size of variables " << sizeof(%s) * 8 << endl;


    return 0;
}




    """ % (
    leavefuncs, vartype, parms, funcbody, histassignments, len(node.scope), vartype, len(node.scope), vartype, vartype)


if __name__ == '__main__':
    with open('../tests/40_eqq.txt', 'r') as myfile:
        eq = myfile.read()
    with open('../tests/40_testdata.txt', 'r') as myfile:
        words = myfile.readline().strip()
        words = words[2:]
        words = words.split(';')

    # feature_names = ["a", "b"]
    # spn = str_to_spn("""
    #     (0.2*(Histogram(a|[ 0., 1., 2.];[0.1, 0.9]) * Histogram(b|[ 0., 2.];[0.2])) +
    #     0.3*(Histogram(a|[ 0., 1., 2.];[0.1, 0.9]) * Histogram(b|[ 0., 2.];[0.2]))
    #     )
    #     """, feature_names, Histograms.str_to_spn_lambdas)

    feature_names = words
    spn = str_to_spn(eq, feature_names, Histograms.str_to_spn_lambdas)

    code = to_cpp(spn, feature_names)

    text_file = open("/tmp/spn.cpp", "w")
    text_file.write(code)
    text_file.close()

    print(code)

    print(subprocess.check_output(['g++', '-O3', '-o', '/tmp/spnexec', '/tmp/spn.cpp']))
    print(subprocess.check_output(['g++', '-O3', '-ffast-math', '-o', '/tmp/spnexecfast', '/tmp/spn.cpp']))
