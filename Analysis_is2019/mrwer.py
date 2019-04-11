#!/usr/bin/python -tt

# this is the main script for MR-WER
# 
# Copyright (C) 2017, Qatar Computing Research Institute, HBKU (author: Ahmed Ali)
#


from __future__ import division
import sys  
import codecs
import collections
import re
from subprocess import call
import numpy as np
from mr import *
import argparse

def werf(r, h):
    # initialisation
    
    D, B = wagner_fischer(r, h)
    bt = naive_backtrace(B)
 
    i,d,s,c,aligned_r, aligned_h, operations = align(r, h, bt)
    return i,d,s,c,len(r),len(h),aligned_r, aligned_h, operations


def load_file_dict (trans_file):
    # we need to handle files with no transcriptions
    dict_map={}
    with codecs.open(trans_file,'r',encoding='utf-8') as h:
        for line in h:
            if len(line.rstrip().split(None, 1)) > 1:
                (key, val) = line.rstrip().split(None, 1)
                dict_map[key] = val
            else: dict_map[line.rstrip()] = ""
    return dict_map

    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Multi reference  evaluation for ASR against one reference or more.')
    parser.add_argument('ref', help='one or more reference transcription',nargs='+')
    parser.add_argument('hyp', help='ASR hypothesis transcription (must be last argument)')
    parser.add_argument('-e', '--show-errors',help='Show error per sentence', action='store_true',default=False)
    parser.add_argument("-ma","--show-multiple-alignment",help='Show multi-reference alignment for each sentence',action="store_true",default=False)
    parser.add_argument("-a","--show-alignment",help='Show alignment for each sentence',action="store_true", default=False)
    
    
    args = parser.parse_args()
    nref=len(args.ref)
    
    load_file_dict (args.hyp)
    
    #load the recognition file 
    hyp_dict = load_file_dict (args.hyp)
    
    #with codecs.open(args.hyp,'r',encoding='utf-8') as h:
    #    hyp_dict = dict(x.rstrip().split(None, 1) for x in h)

    
    #load all the reference files
    ref_dict={}
    align_ref={}
    results_details={}
    total_wer=0

    
    # WER here
    for idx, ref_file in enumerate(args.ref):
        ref_dict[idx]=load_file_dict(ref_file)
        
        #make sure that all files has the same ids
        if not (sorted(ref_dict[idx].keys()) == sorted(hyp_dict.keys())):
            print ("WARNING Files:", ref_file, args.hyp, "have differnt ids.")
            
        i=d=s=c=e=i_t=d_t=s_t=c_t=e_t=wer=wer_t=wc=wc_t=hc=hc_t=0
        align_ref[idx]={}
        
        
        results_details['file_'+str(idx)]={}
        # We calculate the WER per refernce file 
        for key in ref_dict[idx]:
            results_details['file_'+str(idx)]['sent_'+key]={}
            i,d,s,c,wc,hc,results_details['file_'+str(idx)]['sent_'+key]['aligned_r'], \
            results_details['file_'+str(idx)]['sent_'+key]['aligned_h'], \
            results_details['file_'+str(idx)]['sent_'+key]['operations'] = werf(ref_dict[idx][key].split(),hyp_dict[key].split())
            err=i+d+s
            wer=err/wc*100
            i_t+=i
            d_t+=d
            s_t+=s
            c_t+=c
            wc_t+=wc
            hc_t+=hc
            wer='%%WER:%.2f [%d / %d , %d ins, %d del, %s sub]' % (wer,err,wc,i,d,s)
            results_details['file_'+str(idx)]['sent_'+key]['wer']=wer
            
    
        err=i_t+d_t+s_t
        wer=err/wc_t*100
        wer='%%Overall WER:%.2f [%d / %d , %d ins, %d del, %s sub]' % (wer,err,wc_t,i_t,d_t,s_t)
        total_wer+=(err/wc_t)
        results_details['file_'+str(idx)]['wer']=wer
        
        
    # MR-WER here
    i=d=s=c=di=mrwer=i_t=d_t=s_t=c_t=di_t=mrwer_t=0
    # Here, we calculate MR-WER per senetnce across all the available references:
    for sentence_id in hyp_dict.keys():
        results_details['sent_'+sentence_id]={}
        i,d,s,c,di,align_compact,align_details = merge_align(results_details,sentence_id,nref)        
        i_t+=i
        d_t+=d
        s_t+=s
        c_t+=c
        mrwer='%%MR-WER:%.2f [%d ins, %d del, %d sub, %d cor, %d del(uncounted)]' % ((i+d+s)/(s+d+c)*100,i,d,s,c,di)
        results_details['sent_'+sentence_id]['mrwer']=mrwer
        results_details['sent_'+sentence_id]['align_details']=align_details
        results_details['sent_'+sentence_id]['align_compact']=align_compact
        
    mrwer='%%Overall MR-WER:%.2f [%d ins, %d del, %d sub, %d cor]' % ((i_t+d_t+s_t)/(s_t+d_t+c_t)*100,i_t,d_t,s_t,c_t)
    results_details['mrwer']=mrwer
    
    
    #Show results here    
    if args.show_alignment or args.show_multiple_alignment or args.show_errors: 
        print ('Detailed results:')
        for sentence_id in hyp_dict.keys():
            print ('ID:', sentence_id)
            for ref_id in range(nref):
                print ('File:', args.ref[ref_id])
                print (results_details['file_'+str(ref_id)]['sent_'+sentence_id]['wer'])
                if args.show_alignment:
                    print ('Ref: ',' '.join(results_details['file_'+str(ref_id)]['sent_'+sentence_id]['aligned_r']))
                    print ('Hyp:  ',' '.join(results_details['file_'+str(ref_id)]['sent_'+sentence_id]['aligned_h']))
                    print ('Err:  ',' '.join(results_details['file_'+str(ref_id)]['sent_'+sentence_id]['operations']))
                print ('')
            print (results_details['sent_'+sentence_id]['mrwer'])
            if args.show_multiple_alignment:
                print (results_details['sent_'+sentence_id]['align_details'])
            print ('####')
             
    print ('Overall results:')
    for ref_id in range(nref):
        print ('File:', args.ref[ref_id])
        print (results_details['file_'+str(ref_id)]['wer'])
    
    print ('\n', results_details['mrwer'])
    print ('%%Overall AV-WER:%.2f' % (total_wer/nref*100))
    

    
    
    
    
