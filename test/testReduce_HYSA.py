import sys, imp, errno

reduce_script = "reduce_HYSA"
#reduce_script_path = "/SNS/HYSA/shared/autoreduce/" + reduce_script + ".py"
reduce_script_path = "/SNS/users/3qr/workspace/projects/autoreduce/autoreduce/SNSReductionScripts/hyspeca/" + reduce_script + ".py"
print reduce_script
print reduce_script_path

f = open('/tmp/shelly/shelly.txt', 'w')

path = "/SNS/HYSA/IPTS-8562/nexus/HYSA_18901.nxs.h5"
#path = "/SNS/HYS/IPTS-8908/0/15055/NeXus/HYS_15055_event.nxs"
out_dir = "/tmp/shelly/"
#out_dir = "/SNS/HYSA/IPTS-8018/shared/autoreduce/"
print path
print out_dir

try:
  f.write("loading source\n")
  m = imp.load_source(reduce_script, reduce_script_path)
  f.write("init reduction\n")
  reduction = m.AutoReduction(path, out_dir)
  f.write("executing\n")
  reduction.execute()
  f.write("done executing\n")
except ValueError, e:
  print("ValueError: %s " % e)
  f.write("ValueError\n")
except RuntimeError, e:
  print("RuntimeError: %s " % e)
  f.write("RuntimeError\n")
except Exception, e:
  print("Exception: %s " % e)
  f.write("Exception\n")

#if ret == 0:
#    f.write("Reduction passed")
#else:
#    f.write("Exception, see reduction error log")
#f.write(errno)
f.close()
