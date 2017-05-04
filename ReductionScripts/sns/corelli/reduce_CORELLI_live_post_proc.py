import mantid
from mantid.simpleapi import mtd, CloneWorkspace
from finddata import publish_plot
from plotly.offline import plot
import plotly.graph_objs as go
import numpy as np

CloneWorkspace(InputWorkspace=input,OutputWorkspace=output)

runNumber = mtd[output].getRunNumber()
y=mtd[output].extractY()
rowA=np.transpose(y[0:118784].reshape([464,256]))
rowB=np.transpose(y[118784:253952].reshape([528,256]))
rowC=np.transpose(y[253952:372736].reshape([464,256]))
empty=np.empty([256,32])
empty.fill(np.nan)
rowA=np.concatenate((empty,rowA,empty),axis=1)
rowC=np.concatenate((empty,rowC,empty),axis=1)
inst=np.concatenate((rowA,rowB,rowC),axis=0)

colorscale= [
        [0, '#440154'],
        [10**-3.75, '#48186a'],
        [10**-3.5, '#472d7b'],
        [10**-3.23, '#424086'],
        [10**-3, '#3b528b'],
        [10**-2.75, '#33638d'],
        [10**-2.5, '#2c728e'],
        [10**-2.25, '#26828e'],
        [10**-2, '#21918c'],
        [10**-1.75, '#1fa088'],
        [10**-1.5, '#28ae80'],
        [10**-1.25, '#3fbc73'],
        [10**-1, '#5ec962'],
        [10**-0.75, '#84d44b'],
        [10**-0.5, '#addc30'],
        [10**-0.25, '#d8e219'],
        [10**0, '#fde725']]

colorbar={'tick0':0, 'tickmode':'array', 'tickvals':[y.max(),y.max()/10,y.max()/100]}

data=[
    go.Heatmap(z=inst,colorscale=colorscale,colorbar=colorbar)
]

layout=go.Layout(
    xaxis=dict(
        showgrid=False,
        zeroline=False,
        showline=False,
        ticks='',
        showticklabels=False
    ),
    yaxis=dict(
        showgrid=False,
        zeroline=False,
        showline=False,
        ticks='',
        showticklabels=False
    ),
    margin={'l':0,'t':0,'r':0,'b':0}
)

figure=go.Figure(data=data, layout=layout)

div=plot(figure,output_type='div',show_link=False,include_plotlyjs=False)

if runNumber > 0:
    mantid.logger.information('Posting plot of CORELLI_%s' % runNumber)
    request = publish_plot('CORELLI', runNumber, files={'file':div})
    mantid.logger.information("post returned %d" % request.status_code)
    mantid.logger.information("resulting document:")
    mantid.logger.information(str(request.text))
