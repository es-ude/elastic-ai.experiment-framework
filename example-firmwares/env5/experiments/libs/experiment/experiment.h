#ifndef EXPERIMENT_H
#define EXPERIMENT_H

typedef struct Experiment Experiment;

typedef struct ExperimentFns
{
  void (*setup)(Experiment *ctx);
  void (*loop)(Experiment *ctx);
  void (*cleanup)(Experiment *ctx);
} ExperimentFns;

struct Experiment
{
  const ExperimentFns *fns;
};

static void experiment_setup(Experiment *self)
{
  self->fns->setup(self);
}
static void experiment_loop(Experiment *self)
{
  self->fns->loop(self);
}
static void experiment_cleanup(Experiment *self)
{
  self->fns->cleanup(self);
}

#endif // EXPERIMENT_H
