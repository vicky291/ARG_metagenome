#!/usr/bin/env python

'''This script requies 4 input files 2 and output file paths:
	Input:
	(1) (Optional) MicrobeCensus output txt file. 
	(2) (Optional) Organized table of MEGARes database gene length. 
	(3) (Optional) Resistome Analyzer gene level output. Other levels are also included in this file and can be collapsed in final output files if desired. 
	(4) (Optional) A wildcard input indicating normalized tables to be merged. 
	Output:
	(1) (Required for python 2.x) Individual normalized table.
	(2) (Optional) Merged normalized table containg multiple samples from Input(4). Can be omitted to not have a merged table.
	'''

import pandas as pd
import csv
import numpy
import os
import re


# parse input argument 
import argparse
parser = argparse.ArgumentParser(description='Normalize ResistomeAnalyzer output with AMR gene length and sample genome equivalents estimated by MicrobeCensus.')
parser.add_argument('--mc', type=str, help='File path to MicrobeCensus output txt file.', required=False)
parser.add_argument('--genelen', type=str, help='File path to organized gene length table from MEGARes databse.', required=False)
parser.add_argument('--count', type=str, help='File path to count table generated by ResistomeAnalyzer.', required=False)
parser.add_argument('--out', type=str, help='File path to write the normalized count table.', required=False)
# althoug not required for argparse, the wildcard input is required by the merge_normtab() function
parser.add_argument('--mergein', type=str, help='File path to a number of normalized count tables per sample.', nargs='+', required=False) 
parser.add_argument('--mergeout', type=str, help='File path to write the normalized count table.', required=False)
args = vars(parser.parse_args())


# Define function to calculate normalized table
def make_RPKG_normtab(mcfp=None, lenfp=None, countfp=None, outfp=None):
	# 1 # read in MicrobeCensus genome equivalents output
	try:
		mctab = pd.read_csv(mcfp, sep="\t") # read in file
		ge = float(mctab.at['genome_equivalents:', 'Parameters']) # get the value for genome equivalents
	except ValueError: 
		pass

	# 2 # read in organized gene length table ("megares_modified_database_v2_GeneLen_org.tsv")
	try: 
		lentab = pd.read_csv(lenfp, sep='\t', header=0).set_index('MEGID')
		lentab.astype({'Len': 'float'})
	except ValueError:
		pass


	# 3 # read in count table generated by Resistome Analyzer at gene level (also cotains, group, mechanism and class info)
	try:
		countab = pd.read_csv(countfp,
							  names=['Sample','MEGID','Class','Mechanism','Group','Gene','Hits','GeneFrac','DUM','MY'], # add column names
							  sep="\t|[|]|RequiresSNPConfirmation", engine='python',
							  header=None).set_index('MEGID')
		countab = countab.drop('Gene', axis=0) # Remove the first row which contains pre-parsing header
		
		# Remove all the NaN genenrated in the middle of the df due to parsing "RequiresSNPConfirmation"
		for i in countab.index:
			if numpy.isnan(countab.at[i,'Hits']):
				countab.at[i,'Hits'] = countab.at[i,'DUM']
				countab.at[i,'GeneFrac'] = countab.at[i,'MY']
		countab = countab.drop(columns=['DUM','MY'])
	
		# assumes sample name is the character string after the last / and before .tsv
		# The sample name is 5007 from the path /file/to/your/path/5007_gene.tsv
		fn = os.path.basename(countfp) # get the xx_gene.tsv file name
		samid = re.search('(.+?)_gene.tsv', fn).group(1)
		# remove the "align" suffix after sample name
		countab_fin = countab.replace(countab.at[i, 'Sample'], samid) # I hitched the last i value from the previous loop
	except ValueError:
		pass	

	# 4 # Calculate to get the final normalized table 
	try:
		normtab=countab_fin.copy() # initialize with an empty dataframe
		RPKG = [] # initialize with an empty 
		
		for i in normtab.index:
			# equation: Hits/((len in kb)*GE)
			len = float(lentab.at[i,'Len'])/1000
			norm_val = normtab.at[i,'Hits']/(len*ge) 
			RPKG.append(norm_val)
		    
		normtab['RPKG'] = RPKG # add a new column with RPKG
	
		# remove sample column and replace the RPKG column header with sample name
		# remove Sample, Hits and GeneFrac column
		normtab_fin = normtab.rename(columns={'RPKG':normtab.at[i,'Sample']}).drop(columns=['Sample','Hits', 'GeneFrac'])
	except UnboundLocalError:
		pass

	# 5 # Write out the final table
	try: 
		normtab_fin.to_csv(outfp, sep=',') 
	except (TypeError, UnboundLocalError):
		pass	


# Define subsidiary function to merge normalizaed count 
def merge_normtab(mergeout=None, *args):
	try:
		tabm=pd.DataFrame() # initialize with an empty dataframe as merged table
		for file in args:
			tab = pd.read_csv(file, sep=',', header=0)
			try:
				tabm = pd.merge(tab, tabm, how='outer', on = ['MEGID','Class','Mechanism','Group','Gene'])
				tabm.fillna(0, inplace=True) # replace nan from merging by 0
			except KeyError:
				tabm = tab.copy() # the first loop when tabm is an empty df
		tabm.to_csv(mergeout, sep=',')	
	except ValueError: 
		pass	# in python 2, this won't work...*args still requires input

# To ensure that the script can be run by itself (__name__ == "__main__" is true) 
# and individual functions can be imported as modules in other python scripts
if __name__ == "__main__":

	# excute
	make_RPKG_normtab(mcfp=args['mc'], 
					  lenfp=args['genelen'], 
					  countfp=args['count'], 
					  outfp=args['out']) 
	merge_normtab(args['mergeout'], *args['mergein']) # add * to parse the wildcard input to multiple string variables


	




