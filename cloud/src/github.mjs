export async function dispatch(env,id){
 if(!/^[a-zA-Z0-9_.-]+\/[a-zA-Z0-9_.-]+$/.test(env.RUNNER_REPOSITORY||'')||!env.GITHUB_DISPATCH_TOKEN||!env.RUNNER_WORKFLOW||!env.RUNNER_REF)throw Error('Закрытый исполнитель GitHub не подключён');
 const headers={Authorization:'Bearer '+env.GITHUB_DISPATCH_TOKEN,'X-GitHub-Api-Version':'2022-11-28','User-Agent':'order-profit-factory','Accept':'application/vnd.github+json'};
 const meta=await fetch('https://api.github.com/repos/'+env.RUNNER_REPOSITORY,{headers});
 if(!meta.ok||(await meta.json()).private!==true)throw Error('Исполнитель должен находиться в закрытом репозитории');
 const r=await fetch('https://api.github.com/repos/'+env.RUNNER_REPOSITORY+'/actions/workflows/'+encodeURIComponent(env.RUNNER_WORKFLOW)+'/dispatches',{method:'POST',headers:{...headers,'Content-Type':'application/json'},body:JSON.stringify({ref:env.RUNNER_REF,inputs:{job_id:id}})});
 if(r.status!==204)throw Error('GitHub не принял задание; проверьте доступ исполнителя');
}
